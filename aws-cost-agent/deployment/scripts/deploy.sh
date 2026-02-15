#!/bin/bash
set -e

APP_NAME="aws-cost-agent"
APP_DIR="/opt/$APP_NAME"
APP_USER="$APP_NAME"

echo "Deploying AWS Cost AI Agent..."

cd "$APP_DIR"
sudo -u "$APP_USER" git pull origin main

echo "Updating dependencies..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade -r requirements.txt

echo "Restarting service..."
systemctl restart "$APP_NAME"

sleep 5

echo "Performing health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
  echo "✓ Deployment successful!"
  systemctl status "$APP_NAME" --no-pager
else
  echo "✗ Health check failed!"
  journalctl -u "$APP_NAME" -n 50 --no-pager
  exit 1
fi
