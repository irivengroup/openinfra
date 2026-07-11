#!/bin/sh
set -eu

require() {
    name=$1
    eval "value=\${$name:-}"
    if [ -z "$value" ]; then
        echo "openinfra-pgbouncer: missing required environment variable $name" >&2
        exit 2
    fi
}

validate_identifier() {
    name=$1
    value=$2
    case "$value" in
        *[!A-Za-z0-9_.-]*|'')
            echo "openinfra-pgbouncer: $name contains unsupported characters" >&2
            exit 2
            ;;
    esac
}

escape_userlist() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

for variable in \
    PGBOUNCER_DATABASE_HOST \
    PGBOUNCER_DATABASE_PORT \
    PGBOUNCER_DATABASE_NAME \
    PGBOUNCER_DATABASE_USER \
    PGBOUNCER_DATABASE_PASSWORD
do
    require "$variable"
done

validate_identifier PGBOUNCER_DATABASE_HOST "$PGBOUNCER_DATABASE_HOST"
validate_identifier PGBOUNCER_DATABASE_NAME "$PGBOUNCER_DATABASE_NAME"
validate_identifier PGBOUNCER_DATABASE_USER "$PGBOUNCER_DATABASE_USER"
case "$PGBOUNCER_DATABASE_PORT" in
    *[!0-9]*|'') echo "openinfra-pgbouncer: invalid database port" >&2; exit 2 ;;
esac

runtime_dir=${PGBOUNCER_RUNTIME_DIR:-/tmp/openinfra-pgbouncer}
mkdir -p "$runtime_dir"
umask 077

user_escaped=$(escape_userlist "$PGBOUNCER_DATABASE_USER")
password_escaped=$(escape_userlist "$PGBOUNCER_DATABASE_PASSWORD")
printf '"%s" "%s"\n' "$user_escaped" "$password_escaped" > "$runtime_dir/userlist.txt"

cat > "$runtime_dir/pgbouncer.ini" <<EOF_CONFIG
[databases]
${PGBOUNCER_DATABASE_NAME} = host=${PGBOUNCER_DATABASE_HOST} port=${PGBOUNCER_DATABASE_PORT} dbname=${PGBOUNCER_DATABASE_NAME} user=${PGBOUNCER_DATABASE_USER}

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
unix_socket_dir = /tmp
pidfile =
auth_type = scram-sha-256
auth_file = ${runtime_dir}/userlist.txt
pool_mode = transaction
max_client_conn = ${PGBOUNCER_MAX_CLIENT_CONN:-1000}
default_pool_size = ${PGBOUNCER_DEFAULT_POOL_SIZE:-40}
min_pool_size = ${PGBOUNCER_MIN_POOL_SIZE:-4}
reserve_pool_size = ${PGBOUNCER_RESERVE_POOL_SIZE:-10}
reserve_pool_timeout = ${PGBOUNCER_RESERVE_POOL_TIMEOUT:-3}
max_db_connections = ${PGBOUNCER_MAX_DB_CONNECTIONS:-80}
max_db_client_connections = ${PGBOUNCER_MAX_DB_CLIENT_CONNECTIONS:-1000}
server_reset_query = DISCARD ALL
server_reset_query_always = 1
server_check_delay = 5
server_login_retry = 2
server_idle_timeout = 300
server_lifetime = 1800
query_wait_timeout = ${PGBOUNCER_QUERY_WAIT_TIMEOUT:-10}
query_wait_notify = 2
idle_transaction_timeout = ${PGBOUNCER_IDLE_TRANSACTION_TIMEOUT:-60}
transaction_timeout = ${PGBOUNCER_TRANSACTION_TIMEOUT:-120}
max_prepared_statements = 0
ignore_startup_parameters = extra_float_digits,options
application_name_add_host = 1
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
EOF_CONFIG

exec /usr/bin/pgbouncer "$runtime_dir/pgbouncer.ini"
