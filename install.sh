#!/bin/bash

#############################################
#  AWS Cost AI Agent - Installation Script  #
#  Version: 3.1.0                           #
#  Production Ready - Security Hardened     #
#############################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║     🤖 AWS Cost AI Agent v3.1.0 - Installation Wizard    ║"
echo "║                                                           ║"
echo "║     AI-Powered Cost Monitoring with Gemini 3 Flash       ║"
echo "║     Production Ready • Security Hardened                  ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Installation directory
INSTALL_DIR="${INSTALL_DIR:-/opt/aws-cost-agent}"

echo -e "${BLUE}📁 Installation directory: ${INSTALL_DIR}${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}⚠️  This script should be run as root or with sudo${NC}"
   echo "   Run: sudo bash install.sh"
   exit 1
fi

# Check/Install Python 3.11+
echo -e "${BLUE}🔍 Checking Python...${NC}"
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "$PY_VERSION" -ge 10 ]; then
        PYTHON_CMD="python3"
    else
        echo -e "${YELLOW}Installing Python 3.11...${NC}"
        apt update && apt install -y python3.11 python3.11-venv python3-pip
        PYTHON_CMD="python3.11"
    fi
else
    echo -e "${YELLOW}Installing Python 3.11...${NC}"
    apt update && apt install -y python3.11 python3.11-venv python3-pip
    PYTHON_CMD="python3.11"
fi
echo -e "${GREEN}✅ Python ready: $PYTHON_CMD${NC}"

# Create installation directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    🔐 SECURE CONFIGURATION                  ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}All credentials stored in .env file with chmod 600${NC}"
echo -e "${YELLOW}SMTP password stored ONLY in .env (never in S3/JSON)${NC}"
echo ""

# Function to read password securely
read_secret() {
    local prompt="$1"
    local var_name="$2"
    local value=""
    
    echo -ne "${GREEN}$prompt${NC}"
    read -s value
    echo ""
    eval "$var_name='$value'"
}

# Function to read normal input
read_input() {
    local prompt="$1"
    local var_name="$2"
    local default="$3"
    local value=""
    
    if [ -n "$default" ]; then
        echo -ne "${GREEN}$prompt [${default}]: ${NC}"
    else
        echo -ne "${GREEN}$prompt: ${NC}"
    fi
    read value
    
    if [ -z "$value" ] && [ -n "$default" ]; then
        value="$default"
    fi
    
    eval "$var_name='$value'"
}

# Generate secure API key
generate_api_key() {
    openssl rand -base64 32 | tr -d '/+=' | head -c 32
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  0️⃣  API AUTHENTICATION (Required for security)            ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}This key protects your API endpoints from unauthorized access${NC}"
echo -e "${YELLOW}Press Enter to auto-generate a secure key, or enter your own${NC}"
echo ""

DEFAULT_API_KEY=$(generate_api_key)
read_input "Agent API Key" AGENT_API_KEY "$DEFAULT_API_KEY"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  1️⃣  GEMINI AI CONFIGURATION (Required for AI features)    ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Get your free API key from: https://aistudio.google.com/apikey${NC}"
echo ""
read_secret "Enter Gemini API Key: " GEMINI_API_KEY

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  2️⃣  AWS S3 CONFIGURATION                                  ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}RECOMMENDED: Use IAM role if running on EC2 (leave keys blank)${NC}"
echo -e "${YELLOW}Only provide access keys if NOT using IAM role${NC}"
echo ""
read_input "S3 Bucket Name" S3_BUCKET_NAME "aws-cost-agent-data"
read_input "AWS Region" AWS_REGION "us-east-1"
echo ""
echo -e "${YELLOW}Leave blank if using IAM role (recommended for EC2):${NC}"
read_secret "AWS Access Key ID (or blank for IAM role): " AWS_ACCESS_KEY_ID
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    read_secret "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
else
    AWS_SECRET_ACCESS_KEY=""
    echo -e "${GREEN}✅ Will use IAM role for S3 access${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  3️⃣  DATADOG CONFIGURATION (Required for cost data)        ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Get keys from: Datadog → Organization Settings → API Keys${NC}"
echo -e "${YELLOW}Note: Requires Cloud Cost Management feature for accurate data${NC}"
echo ""
read_secret "Datadog API Key: " DATADOG_API_KEY
read_secret "Datadog App Key: " DATADOG_APP_KEY
read_input "Datadog Site" DATADOG_SITE "datadoghq.com"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  4️⃣  EMAIL CONFIGURATION (Required for notifications)      ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}For Outlook/Office 365, use smtp.office365.com${NC}"
echo -e "${YELLOW}SMTP password is stored ONLY in .env (never in S3)${NC}"
echo ""
read_input "SMTP Host" SMTP_HOST "smtp.office365.com"
read_input "SMTP Port" SMTP_PORT "587"
read_input "SMTP Username (email)" SMTP_USER ""
read_secret "SMTP Password: " SMTP_PASSWORD
read_input "Sender Email" SENDER_EMAIL "$SMTP_USER"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  5️⃣  NOTIFICATION SETTINGS                                 ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Schedule times are in UTC timezone${NC}"
echo ""
read_input "Anomaly Threshold (% increase to flag)" ANOMALY_THRESHOLD "20"
read_input "Weekly Report Day (monday-sunday)" SCHEDULE_DAY "monday"
read_input "Weekly Report Hour (0-23 UTC)" SCHEDULE_HOUR "9"
read_input "Admin Email(s) (comma-separated)" ADMIN_EMAILS ""

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    📝 CREATING FILES                        ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Create secure .env file
echo -e "${BLUE}Creating secure .env file...${NC}"
cat > .env << ENVEOF
# AWS Cost AI Agent Configuration v3.1.0
# Generated: $(date)
# ⚠️ KEEP THIS FILE SECURE - DO NOT COMMIT TO GIT
# ⚠️ chmod 600 applied - only root can read

# ==================== API AUTHENTICATION ====================
# Required for all protected API endpoints
# Include in requests as header: X-API-Key: your_key
AGENT_API_KEY=${AGENT_API_KEY}

# Set to 'true' to disable auth (NOT recommended for production)
DISABLE_AUTH=false

# ==================== GEMINI AI ====================
GEMINI_API_KEY=${GEMINI_API_KEY}

# ==================== AWS S3 ====================
S3_BUCKET_NAME=${S3_BUCKET_NAME}
AWS_REGION=${AWS_REGION}
# Leave blank if using IAM role (recommended)
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

# ==================== DATADOG ====================
DATADOG_API_KEY=${DATADOG_API_KEY}
DATADOG_APP_KEY=${DATADOG_APP_KEY}
DATADOG_SITE=${DATADOG_SITE}

# ==================== SMTP (secrets stay here only) ====================
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
SENDER_EMAIL=${SENDER_EMAIL}

# ==================== SETTINGS ====================
ANOMALY_THRESHOLD=${ANOMALY_THRESHOLD}
SCHEDULE_DAY=${SCHEDULE_DAY}
SCHEDULE_HOUR=${SCHEDULE_HOUR}
ADMIN_EMAILS=${ADMIN_EMAILS}
ENVEOF

chmod 600 .env
echo -e "${GREEN}✅ .env file created with secure permissions (600)${NC}"

# Create virtual environment
echo -e "${BLUE}Creating Python virtual environment...${NC}"
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet \
    fastapi \
    uvicorn \
    python-dotenv \
    pydantic \
    email-validator \
    apscheduler \
    httpx \
    boto3 \
    emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Check if server.py exists
if [ ! -f "server.py" ]; then
    echo -e "${YELLOW}⚠️  server.py not found${NC}"
    echo -e "${YELLOW}Please copy server.py to ${INSTALL_DIR}/${NC}"
fi

# Create systemd service
echo -e "${BLUE}Creating systemd service...${NC}"
cat > /etc/systemd/system/aws-cost-agent.service << SERVICEEOF
[Unit]
Description=AWS Cost AI Agent v3.1.0
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${INSTALL_DIR}/venv/bin
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${INSTALL_DIR}

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo -e "${GREEN}✅ Systemd service created (binds to localhost only)${NC}"

# Create .gitignore
cat > .gitignore << 'GITIGNOREEOF'
# Secrets - NEVER COMMIT
.env
*.env

# Python
__pycache__/
*.pyc
venv/

# Data
data/
*.json

# Logs
*.log
GITIGNOREEOF

echo -e "${GREEN}✅ .gitignore created${NC}"

# Start service if server.py exists
if [ -f "server.py" ]; then
    echo ""
    echo -e "${BLUE}Starting AWS Cost AI Agent...${NC}"
    systemctl daemon-reload
    systemctl enable aws-cost-agent
    systemctl start aws-cost-agent
    
    sleep 3
    
    if systemctl is-active --quiet aws-cost-agent; then
        echo -e "${GREEN}✅ Agent is running!${NC}"
    else
        echo -e "${YELLOW}⚠️  Agent may still be starting...${NC}"
        echo -e "${YELLOW}   Check status: systemctl status aws-cost-agent${NC}"
    fi
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    ✅ INSTALLATION COMPLETE                 ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}🎉 AWS Cost AI Agent v3.1.0 has been installed!${NC}"
echo ""
echo -e "${BLUE}📍 Location:${NC}      ${INSTALL_DIR}"
echo -e "${BLUE}🌐 API Endpoint:${NC}  http://localhost:8001/api"
echo -e "${BLUE}📊 Health Check:${NC}  http://localhost:8001/api/health"
echo ""
echo -e "${RED}🔐 YOUR API KEY (save this!):${NC}"
echo -e "${YELLOW}   ${AGENT_API_KEY}${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}                      SECURITY NOTES                         ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${RED}⚠️  API requires authentication!${NC}"
echo -e "  ${BLUE}Include header:${NC} X-API-Key: ${AGENT_API_KEY}"
echo -e "  ${BLUE}Service binds to:${NC} localhost only (127.0.0.1)"
echo -e "  ${BLUE}SMTP password:${NC} stored only in .env (not in S3)"
echo -e "  ${BLUE}Scheduler timezone:${NC} UTC"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}                      COMMANDS                               ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BLUE}Start:${NC}    sudo systemctl start aws-cost-agent"
echo -e "  ${BLUE}Stop:${NC}     sudo systemctl stop aws-cost-agent"
echo -e "  ${BLUE}Restart:${NC}  sudo systemctl restart aws-cost-agent"
echo -e "  ${BLUE}Status:${NC}   sudo systemctl status aws-cost-agent"
echo -e "  ${BLUE}Logs:${NC}     sudo journalctl -u aws-cost-agent -f"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}                      EXAMPLE API CALLS                      ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}1. Health check (no auth required):${NC}"
echo '   curl "http://localhost:8001/api/health"'
echo ""
echo -e "${GREEN}2. Add teams (auth required):${NC}"
echo "   curl -X POST \"http://localhost:8001/api/teams/bulk\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -H \"X-API-Key: ${AGENT_API_KEY}\" \\"
echo '     -d '"'"'[{"team_name":"Team1","aws_account_id":"123456789012","team_email":"team@company.com"}]'"'"
echo ""
echo -e "${GREEN}3. Trigger report (auth required):${NC}"
echo "   curl -X POST \"http://localhost:8001/api/trigger/weekly-report\" \\"
echo "     -H \"X-API-Key: ${AGENT_API_KEY}\""
echo ""
echo -e "${GREEN}4. Get recommendations (auth required):${NC}"
echo "   curl \"http://localhost:8001/api/ai/recommendations\" \\"
echo "     -H \"X-API-Key: ${AGENT_API_KEY}\""
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         Thank you for using AWS Cost AI Agent! 🤖          ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
