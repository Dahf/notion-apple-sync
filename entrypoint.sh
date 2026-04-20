#!/bin/sh
set -e

CONFIG_DIR="/app/config"
mkdir -p "${CONFIG_DIR}"
chown -R appuser:appuser "${CONFIG_DIR}"

exec gosu appuser "$@"
