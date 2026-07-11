#!/bin/sh
set -eu

required_vars="POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD OPENINFRA_POSTGRES_REPLICATION_USER OPENINFRA_POSTGRES_REPLICATION_PASSWORD"
for name in $required_vars; do
    eval "value=\${$name:-}"
    if [ -z "$value" ]; then
        echo "missing required environment variable: $name" >&2
        exit 64
    fi
done

until PGPASSWORD="$POSTGRES_PASSWORD" pg_isready \
    -h "${OPENINFRA_POSTGRES_PRIMARY_HOST:-postgres}" \
    -p "${OPENINFRA_POSTGRES_PRIMARY_PORT:-5432}" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    sleep 1
done

PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -v ON_ERROR_STOP=1 \
    -h "${OPENINFRA_POSTGRES_PRIMARY_HOST:-postgres}" \
    -p "${OPENINFRA_POSTGRES_PRIMARY_PORT:-5432}" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
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
