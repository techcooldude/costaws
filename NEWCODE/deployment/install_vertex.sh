#!/bin/bash
set -e

echo "=========================================="
echo "AWS Cost AI Agent - Vertex AI Installation"
echo "Internal Network Only"
echo "=========================================="

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

APP_NAME="aws-cost-agent"
APP_DIR="/opt/$APP_NAME"
APP_USER="$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"

# Install dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl

# Create user
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
fi

# Create directories
mkdir -p "$APP_DIR"/{data,logs}
mkdir -p "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$LOG_DIR"

# Setup Python venv
echo "Setting up Python environment..."
sudo -u "$APP_USER" python3.11 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# Copy service file
cp deployment/systemd/aws-cost-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $APP_NAME

# Create .env
if [ ! -f "$APP_DIR/.env" ]; then
    cp .env.example "$APP_DIR/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Place GCP service account JSON:"
echo "   sudo cp gcp-service-account.json $APP_DIR/"
echo "   sudo chown $APP_USER:$APP_USER $APP_DIR/gcp-service-account.json"
echo "   sudo chmod 600 $APP_DIR/gcp-service-account.json"
echo ""
echo "2. Edit .env: sudo nano $APP_DIR/.env"
echo ""
echo "3. Start service: sudo systemctl start $APP_NAME"
echo ""
echo "4. Check logs: sudo journalctl -u $APP_NAME -f"
echo ""
echo "Service will be accessible ONLY on localhost:8000"
