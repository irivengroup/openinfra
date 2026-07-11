FROM ghcr.io/cloudnative-pg/pgbouncer:1.25.2@sha256:459b1263c4d5621299e58b1dbf5b33aa71eb1b529c674c0d0d476b1e0f07d973

USER root
COPY docker/pgbouncer/entrypoint.sh /usr/local/bin/openinfra-pgbouncer-entrypoint
RUN chmod 0555 /usr/local/bin/openinfra-pgbouncer-entrypoint
USER pgbouncer

ENTRYPOINT ["/usr/local/bin/openinfra-pgbouncer-entrypoint"]
