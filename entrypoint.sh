#!/bin/sh
set -e

CONFIG_DIR="/app/config"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
EXAMPLE_FILE="/app/config.example.yaml"

mkdir -p "${CONFIG_DIR}"
chown -R appuser:appuser "${CONFIG_DIR}"

if [ ! -f "${CONFIG_FILE}" ]; then
    echo "No config.yaml found — seeding from config.example.yaml"
    cp "${EXAMPLE_FILE}" "${CONFIG_FILE}"
    chown appuser:appuser "${CONFIG_FILE}"
fi

exec gosu appuser "$@"
