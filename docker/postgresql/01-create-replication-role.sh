#!/bin/sh
set -eu

: "${OPENINFRA_POSTGRES_REPLICATION_USER:?replication user is required}"
: "${OPENINFRA_POSTGRES_REPLICATION_PASSWORD:?replication password is required}"

psql --set=ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set=repl_user="$OPENINFRA_POSTGRES_REPLICATION_USER" \
    --set=repl_password="$OPENINFRA_POSTGRES_REPLICATION_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE %I WITH REPLICATION LOGIN PASSWORD %L',
    :'repl_user',
    :'repl_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'repl_user')
\gexec

SELECT format(
    'ALTER ROLE %I WITH REPLICATION LOGIN PASSWORD %L',
    :'repl_user',
    :'repl_password'
)
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'repl_user')
\gexec
SQL
