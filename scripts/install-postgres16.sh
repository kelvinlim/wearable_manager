#!/usr/bin/env bash
# Install Postgres 16 via rootful Podman + Quadlet on RHEL 9.
# Run as: sudo bash /tmp/install-postgres16.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "must run as root: sudo bash $0" >&2
  exit 1
fi

DATA_DIR=/var/lib/pgdata
ETC_DIR=/etc/wearable-manager
ENV_FILE=$ETC_DIR/db.env
QUADLET=/etc/containers/systemd/postgres16.container
PGPASS=/root/.pgpass
IMAGE=docker.io/library/postgres:16
PORT=5432

echo "[1/7] Creating directories"
install -d -m 0755 "$DATA_DIR"
install -d -m 0750 "$ETC_DIR"
install -d -m 0755 /etc/containers/systemd

echo "[2/7] Generating password (only if env file does not exist)"
if [[ ! -f "$ENV_FILE" ]]; then
  PW=$(openssl rand -base64 33 | tr -d '/+=\n' | head -c 32)
  umask 077
  cat > "$ENV_FILE" <<EOF
POSTGRES_PASSWORD=$PW
PGDATA=/var/lib/postgresql/data
EOF
  chmod 0640 "$ENV_FILE"
  chgrp root "$ENV_FILE"
  echo "  wrote $ENV_FILE"

  # /root/.pgpass for convenience: localhost:5432:*:postgres:PW
  printf "localhost:%s:*:postgres:%s\n" "$PORT" "$PW" > "$PGPASS"
  printf "127.0.0.1:%s:*:postgres:%s\n" "$PORT" "$PW" >> "$PGPASS"
  chmod 0600 "$PGPASS"
  echo "  wrote $PGPASS"
else
  echo "  $ENV_FILE already exists; leaving in place"
fi

echo "[3/7] Pulling image $IMAGE"
podman pull "$IMAGE"

echo "[4/7] Writing Quadlet unit $QUADLET"
cat > "$QUADLET" <<EOF
[Unit]
Description=PostgreSQL 16 (wearable_manager)
Wants=network-online.target
After=network-online.target

[Container]
Image=$IMAGE
ContainerName=postgres16
PublishPort=127.0.0.1:$PORT:5432
Volume=$DATA_DIR:/var/lib/postgresql/data
EnvironmentFile=$ENV_FILE
HealthCmd=pg_isready -U postgres
HealthInterval=30s
HealthRetries=5
HealthStartPeriod=60s

[Service]
Restart=on-failure
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target default.target
EOF
chmod 0644 "$QUADLET"

echo "[5/7] systemctl daemon-reload"
systemctl daemon-reload

echo "[6/7] Starting postgres16.service"
systemctl start postgres16.service

echo "[7/7] Waiting for healthy state"
for i in $(seq 1 30); do
  if podman healthcheck run postgres16 >/dev/null 2>&1; then
    echo "  postgres is ready"
    break
  fi
  sleep 2
  if [[ $i -eq 30 ]]; then
    echo "  timed out waiting for healthcheck; check 'systemctl status postgres16' and 'podman logs postgres16'" >&2
    exit 1
  fi
done

echo
echo "Done."
echo "  status:   systemctl status postgres16"
echo "  logs:     podman logs postgres16"
echo "  connect:  PGPASSFILE=/root/.pgpass psql -h 127.0.0.1 -U postgres"
echo "  password: see $ENV_FILE (mode 0640)"
