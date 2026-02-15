#!/bin/bash
#
# AWS Cost AI Agent - Complete Installation Script
# Compatible with: Amazon Linux 2023, Amazon Linux 2, Ubuntu 20.04+, RHEL 8+
# Version: 3.2.0
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
APP_NAME="aws-cost-agent"
APP_USER="$APP_NAME"
APP_DIR="/opt/$APP_NAME"
INSTALL_DIR="$APP_DIR/NEWCODE"
LOG_DIR="/var/log/$APP_NAME"
DATA_DIR="$INSTALL_DIR/data"
SERVICE_FILE="aws-cost-agent.service"

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        print_error "Cannot detect OS"
        exit 1
    fi
    print_info "Detected: $OS $OS_VERSION"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "Please run as root (use sudo)"
        exit 1
    fi
}

show_banner() {
    clear
    echo "═══════════════════════════════════════════════════"
    echo "    AWS Cost AI Agent - Installation"
    echo "    Version 3.2.0 - Internal Network Only"
    echo "═══════════════════════════════════════════════════"
    echo ""
}

install_dependencies() {
    print_info "Installing system dependencies..."
    
    case $OS in
        amzn|amazonlinux)
            yum update -y
            yum install -y python3 python3-pip python3-devel git curl wget gcc make openssl-devel bzip2-devel libffi-devel zlib-devel
            PYTHON_CMD="python3"
            ;;
        ubuntu|debian)
            apt-get update -y
            apt-get install -y python3.11 python3.11-venv python3-pip git curl wget build-essential libssl-dev libffi-dev python3-dev
            PYTHON_CMD="python3.11"
            ;;
        rhel|centos|rocky)
            yum install -y epel-release
            yum update -y
            yum install -y python3 python3-pip python3-devel git curl wget gcc make openssl-devel
            PYTHON_CMD="python3"
            ;;
        *)
            print_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    print_success "Dependencies installed"
}

create_user() {
    print_info "Creating user: $APP_USER"
    if id "$APP_USER" &>/dev/null; then
        print_warning "User exists, skipping..."
    else
        useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
        print_success "User created"
    fi
}

create_directories() {
    print_info "Creating directories..."
    mkdir -p "$APP_DIR" "$INSTALL_DIR" "$LOG_DIR" "$DATA_DIR" "$INSTALL_DIR/logs"
    print_success "Directories created"
}

setup_venv() {
    print_info "Setting up virtual environment..."
    cd "$INSTALL_DIR"
    
    if [ -d "venv" ]; then
        rm -rf venv
    fi
    
    sudo -u "$APP_USER" $PYTHON_CMD -m venv venv
    sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel setuptools
    
    print_success "Virtual environment created"
}

install_python_deps() {
    print_info "Installing Python dependencies..."
    
    if [ ! -f "$INSTALL_DIR/requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    print_success "Python dependencies installed"
}

setup_env() {
    print_info "Setting up .env file..."
    
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        if [ -f "$INSTALL_DIR/.env.example" ]; then
            cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
            chown "$APP_USER:$APP_USER" "$INSTALL_DIR/.env"
            chmod 600 "$INSTALL_DIR/.env"
            print_success "Created .env from .env.example"
            print_warning "⚠️  EDIT: $INSTALL_DIR/.env with your credentials!"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_warning ".env exists, skipping..."
    fi
}

install_service() {
    print_info "Installing systemd service..."
    
    if [ ! -f "$INSTALL_DIR/deployment/systemd/$SERVICE_FILE" ]; then
        print_error "Service file not found"
        exit 1
    fi
    
    cp "$INSTALL_DIR/deployment/systemd/$SERVICE_FILE" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    
    print_success "Service installed and enabled"
}

setup_logrotate() {
    print_info "Configuring log rotation..."
    
    cat > /etc/logrotate.d/$APP_NAME <<EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $APP_USER $APP_USER
    sharedscripts
    postrotate
        systemctl reload $APP_NAME > /dev/null 2>&1 || true
    endscript
}
EOF
    
    print_success "Log rotation configured"
}

set_permissions() {
    print_info "Setting permissions..."
    
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
    
    chmod 755 "$APP_DIR" "$INSTALL_DIR"
    chmod 750 "$DATA_DIR" "$LOG_DIR"
    
    if [ -f "$INSTALL_DIR/.env" ]; then
        chmod 600 "$INSTALL_DIR/.env"
    fi
    
    if [ -d "$INSTALL_DIR/deployment/scripts" ]; then
        chmod +x "$INSTALL_DIR/deployment/scripts/"*.sh
    fi
    
    print_success "Permissions set"
}

verify_installation() {
    print_info "Verifying installation..."
    
    local errors=0
    
    # Check Python
    if sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/python" --version &>/dev/null; then
        print_success "Python: OK"
    else
        print_error "Python: FAILED"
        ((errors++))
    fi
    
    # Check critical files
    for file in "$INSTALL_DIR/app/main.py" "$INSTALL_DIR/app/config.py" "$INSTALL_DIR/app/services/vertex_ai_service.py" "$INSTALL_DIR/.env"; do
        if [ -f "$file" ]; then
            print_success "File: $(basename $file)"
        else
            print_error "Missing: $file"
            ((errors++))
        fi
    done
    
    # Check service
    if systemctl is-enabled "$APP_NAME" &>/dev/null; then
        print_success "Service: Enabled"
    else
        print_error "Service: NOT enabled"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "All checks passed!"
        return 0
    else
        print_error "Found $errors error(s)"
        return 1
    fi
}

print_instructions() {
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "         Installation Complete!"
    echo "═══════════════════════════════════════════════════"
    echo ""
    echo "NEXT STEPS:"
    echo ""
    echo "1. Configure environment:"
    echo "   sudo nano $INSTALL_DIR/.env"
    echo ""
    echo "2. Add GCP credentials:"
    echo "   sudo cp gcp-service-account.json $INSTALL_DIR/"
    echo "   sudo chown $APP_USER:$APP_USER $INSTALL_DIR/gcp-service-account.json"
    echo "   sudo chmod 600 $INSTALL_DIR/gcp-service-account.json"
    echo ""
    echo "3. Start service:"
    echo "   sudo systemctl start $APP_NAME"
    echo ""
    echo "4. Check status:"
    echo "   sudo systemctl status $APP_NAME"
    echo ""
    echo "5. View logs:"
    echo "   sudo journalctl -u $APP_NAME -f"
    echo ""
    echo "6. Test:"
    echo "   curl http://localhost:8000/health"
    echo ""
    echo "═══════════════════════════════════════════════════"
}

main() {
    show_banner
    check_root
    detect_os
    
    install_dependencies
    create_user
    create_directories
    setup_venv
    install_python_deps
    setup_env
    install_service
    setup_logrotate
    set_permissions
    
    echo ""
    if verify_installation; then
        print_instructions
        exit 0
    else
        print_error "Installation completed with errors"
        exit 1
    fi
}

main "$@"
