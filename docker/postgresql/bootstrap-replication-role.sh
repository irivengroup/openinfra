#!/bin/sh
set -eu

required_vars="POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD PGDATA OPENINFRA_POSTGRES_REPLICATION_USER OPENINFRA_POSTGRES_REPLICATION_PASSWORD OPENINFRA_POSTGRES_REPLICATION_CIDR"
for name in $required_vars; do
    eval "value=\${$name:-}"
    if [ -z "$value" ]; then
        echo "missing required environment variable: $name" >&2
        exit 64
    fi
done

case "$OPENINFRA_POSTGRES_REPLICATION_USER" in
    *[!A-Za-z0-9_.-]*|'')
        echo "replication user contains unsupported pg_hba.conf characters" >&2
        exit 64
        ;;
esac

primary_host=${OPENINFRA_POSTGRES_PRIMARY_HOST:-postgres}
primary_port=${OPENINFRA_POSTGRES_PRIMARY_PORT:-5432}

until PGPASSWORD="$POSTGRES_PASSWORD" pg_isready \
    -h "$primary_host" \
    -p "$primary_port" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    sleep 1
done

psql_primary() {
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -v ON_ERROR_STOP=1 \
        -h "$primary_host" \
        -p "$primary_port" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
}

psql_primary \
    --set=replication_user="$OPENINFRA_POSTGRES_REPLICATION_USER" \
    --set=replication_password="$OPENINFRA_POSTGRES_REPLICATION_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE %I WITH LOGIN REPLICATION PASSWORD %L',
    :'replication_user',
    :'replication_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'replication_user'
) \gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN REPLICATION PASSWORD %L',
    :'replication_user',
    :'replication_password'
) \gexec
SQL

hba_file=$(psql_primary -Atqc 'SHOW hba_file')
case "$hba_file" in
    "$PGDATA"/*) ;;
    *)
        echo "refusing to modify pg_hba.conf outside PGDATA: $hba_file" >&2
        exit 65
        ;;
esac

if [ ! -f "$hba_file" ] || [ ! -w "$hba_file" ]; then
    echo "pg_hba.conf is missing or not writable: $hba_file" >&2
    exit 73
fi

hba_rule="host replication $OPENINFRA_POSTGRES_REPLICATION_USER $OPENINFRA_POSTGRES_REPLICATION_CIDR scram-sha-256"
if ! awk \
    -v replication_user="$OPENINFRA_POSTGRES_REPLICATION_USER" \
    -v replication_cidr="$OPENINFRA_POSTGRES_REPLICATION_CIDR" '
        $1 == "host" &&
        $2 == "replication" &&
        $3 == replication_user &&
        $4 == replication_cidr &&
        $5 == "scram-sha-256" { found = 1 }
        END { exit(found ? 0 : 1) }
    ' "$hba_file"; then
    temporary_hba="${hba_file}.openinfra.$$"
    trap 'rm -f "${temporary_hba:-}"' EXIT HUP INT TERM
    current_mode=$(stat -c '%a' "$hba_file")
    {
        printf '%s\n' '# Managed by OpenInfra: physical replication access.'
        printf '%s\n' "$hba_rule"
        cat "$hba_file"
    } > "$temporary_hba"
    chmod "$current_mode" "$temporary_hba"
    mv "$temporary_hba" "$hba_file"
    trap - EXIT HUP INT TERM
fi

reload_result=$(psql_primary -Atqc 'SELECT pg_reload_conf()')
if [ "$reload_result" != "t" ]; then
    echo "PostgreSQL rejected the pg_hba.conf reload" >&2
    exit 70
fi

matching_rules=$(psql_primary \
    -Atqc "SELECT count(*) FROM pg_hba_file_rules WHERE type = 'host' AND 'replication' = ANY(database) AND '$OPENINFRA_POSTGRES_REPLICATION_USER' = ANY(user_name) AND auth_method = 'scram-sha-256' AND error IS NULL")
hba_errors=$(psql_primary -Atqc "SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL")
if [ "$matching_rules" -lt 1 ] || [ "$hba_errors" -ne 0 ]; then
    echo "the replication pg_hba.conf rule was not loaded successfully" >&2
    psql_primary -c "SELECT line_number, type, database, user_name, address, netmask, auth_method, error FROM pg_hba_file_rules WHERE error IS NOT NULL OR 'replication' = ANY(database)" >&2 || true
    exit 78
fi

printf '%s\n' "replication role and pg_hba.conf rule are ready for $OPENINFRA_POSTGRES_REPLICATION_CIDR"
