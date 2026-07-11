#!/bin/sh
set -eu

: "${PGDATA:?PGDATA is required}"
if [ "$(id -u)" = "0" ]; then
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    exec gosu postgres "$0" "$@"
fi

: "${OPENINFRA_POSTGRES_PRIMARY_HOST:?primary host is required}"
: "${OPENINFRA_POSTGRES_REPLICATION_USER:?replication user is required}"
: "${OPENINFRA_POSTGRES_REPLICATION_PASSWORD:?replication password is required}"

initialization_marker="$PGDATA/.openinfra-basebackup-complete"
if [ ! -f "$initialization_marker" ] \
    && [ -s "$PGDATA/PG_VERSION" ] \
    && [ -f "$PGDATA/standby.signal" ] \
    && grep -q '^primary_conninfo' "$PGDATA/postgresql.auto.conf" 2>/dev/null; then
    touch "$initialization_marker"
fi

if [ ! -f "$initialization_marker" ]; then
    find "$PGDATA" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
    export PGPASSWORD=$OPENINFRA_POSTGRES_REPLICATION_PASSWORD
    until pg_isready -h "$OPENINFRA_POSTGRES_PRIMARY_HOST" -p 5432 >/dev/null 2>&1; do
        sleep 1
    done
    pg_basebackup \
        --host="$OPENINFRA_POSTGRES_PRIMARY_HOST" \
        --port=5432 \
        --username="$OPENINFRA_POSTGRES_REPLICATION_USER" \
        --pgdata="$PGDATA" \
        --format=plain \
        --wal-method=stream \
        --write-recovery-conf \
        --checkpoint=fast \
        --no-password
    unset PGPASSWORD

    if [ ! -s "$PGDATA/PG_VERSION" ] || [ ! -f "$PGDATA/standby.signal" ]; then
        echo "pg_basebackup completed without a valid standby layout" >&2
        exit 70
    fi
    touch "$initialization_marker"
fi

exec docker-entrypoint.sh postgres \
    -c hot_standby=on \
    -c max_connections=120 \
    -c shared_buffers=256MB \
    -c log_min_duration_statement=500
