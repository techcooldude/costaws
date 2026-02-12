# AWS Cost Notification Agent

## Complete Installation & Setup Guide

A backend automation system that monitors AWS costs across 84 accounts, detects anomalies, and sends weekly email reports to teams and admins.

---

## Table of Contents

1. [What You Need (Prerequisites)](#what-you-need-prerequisites)
2. [Server Requirements](#server-requirements)
3. [Architecture Overview](#architecture-overview)
4. [Installation Options](#installation-options)
5. [Step-by-Step Setup](#step-by-step-setup)
6. [Configuration Guide](#configuration-guide)
7. [Adding Your 84 Teams](#adding-your-84-teams)
8. [Testing Everything](#testing-everything)
9. [Going Live](#going-live)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

---

## What You Need (Prerequisites)

### 1. Datadog Account & API Keys
You need these from Datadog to fetch AWS cost data:

| Credential | Where to Get It | Purpose |
|------------|-----------------|---------|
| **API Key** | Datadog → Organization Settings → API Keys → New Key | Read access to metrics |
| **Application Key** | Datadog → Organization Settings → Application Keys → New Key | Advanced API operations |
| **Site** | Check your Datadog URL | `datadoghq.com` (US) or `datadoghq.eu` (EU) |

**How to get Datadog keys:**
1. Login to https://app.datadoghq.com (or your EU URL)
2. Click your profile icon → Organization Settings
3. Go to "API Keys" → Click "New Key" → Copy the key
4. Go to "Application Keys" → Click "New Key" → Copy the key

### 2. Email (SMTP) Credentials
For sending emails to Outlook/Office 365:

| Setting | Value for Office 365 |
|---------|---------------------|
| SMTP Host | `smtp.office365.com` |
| SMTP Port | `587` |
| SMTP User | Your email (e.g., `aws-notifications@yourcompany.com`) |
| SMTP Password | Your password or App Password |
| Sender Email | Same as SMTP User |

**Note:** If your organization uses MFA, you'll need to create an "App Password" in Microsoft 365.

### 3. Team Mapping Data
You need a list of your 84 teams with:
- Team name
- AWS Account ID (12 digits)
- Team email address

Example format:
```csv
team_name,aws_account_id,team_email
Platform Team,123456789012,platform@yourcompany.com
DevOps Team,234567890123,devops@yourcompany.com
Data Science,345678901234,datascience@yourcompany.com
...
```

---

## Server Requirements

### Do I Need a Server?

**YES** - This is a backend service that needs to run continuously to:
1. Execute scheduled weekly jobs
2. Serve API endpoints
3. Connect to MongoDB database

### Server Options

| Option | Cost | Difficulty | Recommended For |
|--------|------|------------|-----------------|
| **AWS EC2 (t3.small)** | ~$15/month | Medium | Production |
| **AWS Lambda + EventBridge** | ~$1/month | Hard | Cost-conscious |
| **Docker on existing server** | $0 extra | Easy | If you have infra |
| **Azure App Service** | ~$13/month | Easy | Microsoft shops |
| **DigitalOcean Droplet** | $6/month | Easy | Budget option |
| **Your laptop (testing only)** | $0 | Easy | Development only |

### Minimum Server Specs

```
CPU: 1 vCPU
RAM: 1 GB (2 GB recommended)
Storage: 10 GB
OS: Ubuntu 22.04 LTS (recommended) or any Linux
Network: Outbound access to:
  - api.datadoghq.com (port 443)
  - smtp.office365.com (port 587)
  - MongoDB (port 27017)
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              YOUR SERVER                                 │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     AWS COST NOTIFICATION AGENT                     │ │
│  │                         (Python FastAPI)                            │ │
│  │                                                                     │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │ │
│  │  │  DATADOG    │──►│   COST      │──►│   EMAIL     │              │ │
│  │  │  SERVICE    │   │  ANALYZER   │   │  SERVICE    │              │ │
│  │  └─────────────┘   └─────────────┘   └─────────────┘              │ │
│  │         │                 │                 │                      │ │
│  │         ▼                 ▼                 ▼                      │ │
│  │   Fetch costs      Compare months    Send HTML emails             │ │
│  │   from Datadog     Detect anomalies  to teams & admins            │ │
│  │                                                                     │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │                    SCHEDULER (APScheduler)                    │ │ │
│  │  │              Runs every Monday at 9:00 AM UTC                 │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         MONGODB DATABASE                            │ │
│  │  • teams              - Your 84 team/account mappings               │ │
│  │  • cost_history       - Historical cost records                     │ │
│  │  • anomalies          - Detected cost spikes                        │ │
│  │  • notification_config - Settings (threshold, schedule, emails)     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                │                                          │
                ▼                                          ▼
    ┌───────────────────┐                    ┌───────────────────┐
    │     DATADOG       │                    │   OUTLOOK/SMTP    │
    │   (Cost Data)     │                    │   (Send Emails)   │
    └───────────────────┘                    └───────────────────┘
```

---

## Installation Options

### Option A: Docker (Recommended)

**Best for:** Quick setup, isolated environment, easy updates

### Option B: Direct Installation on Linux Server

**Best for:** Full control, custom configurations

### Option C: AWS Lambda (Serverless)

**Best for:** Cost-conscious, infrequent runs only

---

## Step-by-Step Setup

### Option A: Docker Installation

#### Step 1: Install Docker on Your Server

```bash
# Connect to your server
ssh user@your-server-ip

# Install Docker (Ubuntu/Debian)
sudo apt update
sudo apt install -y docker.io docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker-compose --version
```

#### Step 2: Create Project Directory

```bash
# Create directory
mkdir -p /opt/aws-cost-agent
cd /opt/aws-cost-agent
```

#### Step 3: Create docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: cost-agent-mongodb
    restart: always
    volumes:
      - mongodb_data:/data/db
    networks:
      - cost-agent-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: cost-agent-backend
    restart: always
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=aws_cost_agent
      - DATADOG_API_KEY=${DATADOG_API_KEY}
      - DATADOG_APP_KEY=${DATADOG_APP_KEY}
      - DATADOG_SITE=${DATADOG_SITE:-datadoghq.com}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SENDER_EMAIL=${SENDER_EMAIL}
    depends_on:
      - mongodb
    networks:
      - cost-agent-network

volumes:
  mongodb_data:

networks:
  cost-agent-network:
    driver: bridge
EOF
```

#### Step 4: Create Backend Directory & Dockerfile

```bash
mkdir -p backend
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
EOF
```

#### Step 5: Create requirements.txt

```bash
cat > backend/requirements.txt << 'EOF'
fastapi==0.110.1
uvicorn==0.25.0
python-dotenv>=1.0.1
pymongo==4.5.0
motor==3.3.1
pydantic>=2.6.4
email-validator>=2.2.0
apscheduler>=3.10.0
httpx>=0.25.0
EOF
```

#### Step 6: Copy server.py

Copy the `server.py` file from this repository to `backend/server.py`

```bash
# If you have the file locally
cp /path/to/server.py backend/server.py

# Or download it
curl -o backend/server.py https://your-repo-url/server.py
```

#### Step 7: Create Environment File

```bash
cat > .env << 'EOF'
# Datadog Configuration
DATADOG_API_KEY=your_datadog_api_key_here
DATADOG_APP_KEY=your_datadog_app_key_here
DATADOG_SITE=datadoghq.com

# SMTP Configuration (Office 365)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=aws-notifications@yourcompany.com
SMTP_PASSWORD=your_email_password_here
SENDER_EMAIL=aws-notifications@yourcompany.com
EOF

# Secure the file
chmod 600 .env
```

#### Step 8: Start the Services

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

#### Step 9: Verify Installation

```bash
# Test the API
curl http://localhost:8001/api/health

# Expected response:
# {"status":"healthy","timestamp":"2026-02-12T10:00:00+00:00"}
```

---

### Option B: Direct Linux Installation

#### Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### Step 2: Create Application User

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash costapp
sudo su - costapp
```

#### Step 3: Setup Application

```bash
# Create directory
mkdir -p ~/aws-cost-agent
cd ~/aws-cost-agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-dotenv pymongo motor pydantic email-validator apscheduler httpx
```

#### Step 4: Create Environment File

```bash
cat > .env << 'EOF'
MONGO_URL=mongodb://localhost:27017
DB_NAME=aws_cost_agent

# Datadog
DATADOG_API_KEY=your_datadog_api_key_here
DATADOG_APP_KEY=your_datadog_app_key_here
DATADOG_SITE=datadoghq.com

# SMTP
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=aws-notifications@yourcompany.com
SMTP_PASSWORD=your_email_password_here
SENDER_EMAIL=aws-notifications@yourcompany.com
EOF

chmod 600 .env
```

#### Step 5: Copy server.py

Copy the `server.py` file to `~/aws-cost-agent/server.py`

#### Step 6: Create Systemd Service

```bash
sudo cat > /etc/systemd/system/aws-cost-agent.service << 'EOF'
[Unit]
Description=AWS Cost Notification Agent
After=network.target mongod.service

[Service]
Type=simple
User=costapp
WorkingDirectory=/home/costapp/aws-cost-agent
Environment=PATH=/home/costapp/aws-cost-agent/venv/bin
ExecStart=/home/costapp/aws-cost-agent/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl start aws-cost-agent
sudo systemctl enable aws-cost-agent

# Check status
sudo systemctl status aws-cost-agent
```

---

## Configuration Guide

### Step 1: Access the API

```bash
# If using Docker
API_URL="http://localhost:8001"

# If using remote server
API_URL="http://your-server-ip:8001"
```

### Step 2: Configure Notification Settings

```bash
curl -X PUT "$API_URL/api/config" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_threshold": 20,
    "schedule_day": "monday",
    "schedule_hour": 9,
    "global_admin_emails": [
      "admin1@yourcompany.com",
      "admin2@yourcompany.com",
      "finance-team@yourcompany.com"
    ]
  }'
```

**Configuration Options:**

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `anomaly_threshold` | float | 20.0 | % increase to flag as anomaly |
| `schedule_day` | string | "monday" | Day of weekly report |
| `schedule_hour` | int | 9 | Hour in UTC (0-23) |
| `global_admin_emails` | list | [] | Emails receiving consolidated report |
| `smtp_host` | string | "" | SMTP server (can also set in .env) |
| `smtp_port` | int | 587 | SMTP port |
| `smtp_user` | string | "" | SMTP username |
| `smtp_password` | string | "" | SMTP password |
| `sender_email` | string | "" | From address |

### Step 3: Verify Configuration

```bash
curl "$API_URL/api/config" | python3 -m json.tool
```

---

## Adding Your 84 Teams

### Method 1: Bulk Upload via API (Recommended)

#### Create a JSON file with all teams:

```bash
cat > teams.json << 'EOF'
[
  {"team_name": "Platform Team", "aws_account_id": "123456789012", "team_email": "platform@yourcompany.com"},
  {"team_name": "DevOps Team", "aws_account_id": "234567890123", "team_email": "devops@yourcompany.com"},
  {"team_name": "Data Science", "aws_account_id": "345678901234", "team_email": "datascience@yourcompany.com"},
  {"team_name": "Frontend Team", "aws_account_id": "456789012345", "team_email": "frontend@yourcompany.com"},
  {"team_name": "Backend Team", "aws_account_id": "567890123456", "team_email": "backend@yourcompany.com"}
]
EOF
```

#### Upload to API:

```bash
curl -X POST "$API_URL/api/teams/bulk" \
  -H "Content-Type: application/json" \
  -d @teams.json
```

### Method 2: Convert from CSV

If you have a CSV file:

```bash
# teams.csv format:
# team_name,aws_account_id,team_email
# Platform Team,123456789012,platform@yourcompany.com

# Convert CSV to JSON and upload
python3 << 'EOF'
import csv
import json
import requests

teams = []
with open('teams.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        teams.append({
            "team_name": row['team_name'],
            "aws_account_id": row['aws_account_id'],
            "team_email": row['team_email']
        })

response = requests.post(
    "http://localhost:8001/api/teams/bulk",
    json=teams
)
print(response.json())
EOF
```

### Method 3: Add Teams One by One

```bash
curl -X POST "$API_URL/api/teams" \
  -H "Content-Type: application/json" \
  -d '{
    "team_name": "Platform Team",
    "aws_account_id": "123456789012",
    "team_email": "platform@yourcompany.com",
    "admin_emails": ["team-lead@yourcompany.com"]
  }'
```

### Verify Teams Added

```bash
# Count teams
curl "$API_URL/api/teams" | python3 -c "import sys,json; print(f'Total teams: {len(json.load(sys.stdin))}')"

# List all teams
curl "$API_URL/api/teams" | python3 -m json.tool
```

---

## Testing Everything

### Test 1: Health Check

```bash
curl "$API_URL/api/health"
# Expected: {"status":"healthy","timestamp":"..."}
```

### Test 2: Scheduler Status

```bash
curl "$API_URL/api/scheduler/status"
# Expected: {"running":true,"jobs":[{"id":"weekly_cost_report",...}]}
```

### Test 3: Preview Team Report (Without Sending)

```bash
# Get a team ID first
TEAM_ID=$(curl -s "$API_URL/api/teams" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Preview the report
curl "$API_URL/api/preview/team-report/$TEAM_ID" | python3 -m json.tool
```

### Test 4: Preview Admin Report (Without Sending)

```bash
curl "$API_URL/api/preview/admin-report" | python3 -m json.tool
```

### Test 5: Trigger Manual Report (Sends Actual Emails)

```bash
# Only do this when SMTP is configured!
curl -X POST "$API_URL/api/trigger/weekly-report"
```

### Test 6: Check Logs After Manual Trigger

```bash
# Docker
docker-compose logs -f backend

# Systemd
sudo journalctl -u aws-cost-agent -f
```

---

## Going Live

### Pre-Launch Checklist

- [ ] Datadog API keys added to .env
- [ ] SMTP credentials added to .env
- [ ] All 84 teams imported
- [ ] Admin emails configured
- [ ] Anomaly threshold set appropriately
- [ ] Schedule day/hour configured (UTC timezone!)
- [ ] Test email sent successfully
- [ ] Preview reports look correct

### Monitor the System

```bash
# Check scheduler next run
curl "$API_URL/api/scheduler/status"

# View recent anomalies
curl "$API_URL/api/anomalies?limit=10"

# View cost history
curl "$API_URL/api/costs/history?limit=10"
```

### Set Up Monitoring (Recommended)

Add a health check to your monitoring system:

```bash
# Simple health check script
curl -sf "$API_URL/api/health" || echo "AWS Cost Agent DOWN!"
```

---

## Troubleshooting

### Problem: "Datadog credentials not configured"

**Solution:** Add keys to .env file:
```bash
DATADOG_API_KEY=your_key_here
DATADOG_APP_KEY=your_key_here
```
Then restart the service.

### Problem: "SMTP not configured"

**Solution:** Add email settings:
```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
SENDER_EMAIL=your@email.com
```

### Problem: Emails not being received

**Checklist:**
1. Check spam folder
2. Verify SMTP credentials
3. Try with Gmail first (smtp.gmail.com, port 587)
4. Check firewall allows outbound port 587
5. For Office 365 with MFA, use App Password

### Problem: No cost data from Datadog

**Checklist:**
1. Verify AWS Cost Management integration is enabled in Datadog
2. Check `aws.cost.*` metrics exist in Datadog
3. Verify API key has read permissions
4. Check Datadog site is correct (US vs EU)

### Problem: Scheduler not running

```bash
# Check status
curl "$API_URL/api/scheduler/status"

# If not running, restart the service
docker-compose restart backend
# or
sudo systemctl restart aws-cost-agent
```

### View Logs

```bash
# Docker
docker-compose logs -f backend

# Systemd
sudo journalctl -u aws-cost-agent -f

# Look for errors like:
# - "Failed to connect to Datadog"
# - "SMTP authentication failed"
# - "MongoDB connection error"
```

---

## API Reference

### Base URL
```
http://your-server:8001/api
```

### Endpoints

#### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Agent info |
| GET | `/health` | Health check |
| GET | `/scheduler/status` | Scheduler status |

#### Teams
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/teams` | List all teams |
| POST | `/teams` | Create team |
| GET | `/teams/{id}` | Get team |
| DELETE | `/teams/{id}` | Delete team |
| POST | `/teams/bulk` | Bulk create |

#### Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/config` | Get config |
| PUT | `/config` | Update config |

#### Cost Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/costs/history` | Cost history |
| GET | `/anomalies` | Anomalies list |

#### Triggers & Previews
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/trigger/weekly-report` | Run report now |
| POST | `/trigger/team-report/{id}` | Single team report |
| GET | `/preview/team-report/{id}` | Preview team email |
| GET | `/preview/admin-report` | Preview admin email |

---

## Security Recommendations

1. **Use HTTPS** - Put a reverse proxy (nginx) in front with SSL
2. **Add Authentication** - Consider adding JWT auth for API access
3. **Firewall** - Only allow necessary ports (8001 from trusted IPs)
4. **Secrets Management** - Use AWS Secrets Manager or HashiCorp Vault in production
5. **Regular Updates** - Keep dependencies updated

---

## Support

If you encounter issues:
1. Check this README's Troubleshooting section
2. Review the logs for error messages
3. Verify all prerequisites are met
4. Test with mock data first (remove Datadog keys)

---

## File Structure

```
/opt/aws-cost-agent/
├── docker-compose.yml      # Docker orchestration
├── .env                    # Environment variables (secrets)
├── backend/
│   ├── Dockerfile          # Container definition
│   ├── requirements.txt    # Python dependencies
│   └── server.py           # Main application code
└── teams.json              # Your 84 teams (optional)
```
