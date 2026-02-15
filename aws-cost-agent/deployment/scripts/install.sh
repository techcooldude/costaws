#!/bin/bash
set -e

echo "==================================="
echo "AWS Cost AI Agent - Installation"
echo "==================================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

APP_NAME="aws-cost-agent"
APP_USER="$APP_NAME"
APP_DIR="/opt/$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"
PYTHON_VERSION="3.11"

echo "Installing system dependencies..."
apt-get update
apt-get install -y \
  python${PYTHON_VERSION} \
  python${PYTHON_VERSION}-venv \
  python3-pip \
  nginx \
  git \
  curl \
  supervisor \
  logrotate

if ! id "$APP_USER" &>/dev/null; then
  echo "Creating application user: $APP_USER"
  useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
fi

echo "Creating application directories..."
mkdir -p "$APP_DIR"/{data,logs}
mkdir -p "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$LOG_DIR"

# NOTE: You must place code into $APP_DIR before running pip install.

if [ ! -f "$APP_DIR/requirements.txt" ]; then
  echo "ERROR: $APP_DIR/requirements.txt not found. Clone/copy the project into $APP_DIR first."
  exit 1
fi

echo "Setting up Python virtual environment..."
sudo -u "$APP_USER" python${PYTHON_VERSION} -m venv "$APP_DIR/venv"

echo "Installing Python dependencies..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "Installing systemd service..."
cp deployment/systemd/${APP_NAME}.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ${APP_NAME}

echo "Configuring log rotation..."
cat > /etc/logrotate.d/${APP_NAME} <<EOF
${LOG_DIR}/*.log {
  daily
  missingok
  rotate 14
  compress
  delaycompress
  notifempty
  create 0640 ${APP_USER} ${APP_USER}
  sharedscripts
  postrotate
    systemctl reload ${APP_NAME} > /dev/null 2>&1 || true
  endscript
}
EOF

echo "Configuring Nginx..."
cp deployment/nginx/${APP_NAME}.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/${APP_NAME}.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

if [ ! -f "$APP_DIR/.env" ]; then
  echo "Creating .env file from template..."
  cp .env.example "$APP_DIR/.env" || true
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env" || true
  chmod 600 "$APP_DIR/.env" || true
  echo "⚠️  Please edit $APP_DIR/.env with your configuration"
fi

echo ""
echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo "Next steps:"
echo "1. Edit configuration: sudo nano $APP_DIR/.env"
echo "2. Start the service: sudo systemctl start $APP_NAME"
echo "3. Check status: sudo systemctl status $APP_NAME"
echo "4. View logs: sudo journalctl -u $APP_NAME -f"
