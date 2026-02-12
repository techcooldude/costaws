# AWS Cost Notification Agent (S3 Storage Version)

## Complete Installation & Setup Guide

A **serverless-friendly** backend automation system that monitors AWS costs across 84 accounts, detects anomalies, and sends weekly email reports. **Uses AWS S3 for storage - NO DATABASE REQUIRED!**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [What You Need (Prerequisites)](#what-you-need-prerequisites)
3. [Server Requirements](#server-requirements)
4. [S3 Bucket Structure](#s3-bucket-structure)
5. [Step-by-Step Installation](#step-by-step-installation)
6. [Configuration Guide](#configuration-guide)
7. [Adding Your 84 Teams](#adding-your-84-teams)
8. [Testing Everything](#testing-everything)
9. [Going Live](#going-live)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YOUR SERVER / LAMBDA                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    AWS COST NOTIFICATION AGENT                          │ │
│  │                       (Python FastAPI v2.0)                             │ │
│  │                                                                         │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │ │
│  │  │   DATADOG    │───►│    COST      │───►│    EMAIL     │             │ │
│  │  │   SERVICE    │    │   ANALYZER   │    │   SERVICE    │             │ │
│  │  └──────────────┘    └──────────────┘    └──────────────┘             │ │
│  │         │                   │                   │                      │ │
│  │         ▼                   ▼                   ▼                      │ │
│  │   Fetch aws.cost.*    Compare months      Send HTML emails            │ │
│  │   from Datadog        Detect anomalies    Teams + Admins              │ │
│  │                                                                         │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    SCHEDULER (APScheduler)                         │ │ │
│  │  │              Configurable: Day + Hour (UTC)                        │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
└─────────────────────────────────────│────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS S3 BUCKET                                   │
│                         (aws-cost-agent-data)                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                                                                          ││
│  │   📁 config/                                                            ││
│  │   └── notification_config.json     ← Settings, thresholds, admin emails ││
│  │                                                                          ││
│  │   📁 teams/                                                             ││
│  │   └── teams.json                   ← All 84 team/account mappings       ││
│  │                                                                          ││
│  │   📁 costs/                                                             ││
│  │   └── 2026/                                                             ││
│  │       └── 02/                                                           ││
│  │           ├── 123456789012.json    ← Cost history per account           ││
│  │           ├── 234567890123.json                                         ││
│  │           └── ...                                                       ││
│  │                                                                          ││
│  │   📁 anomalies/                                                         ││
│  │   └── 2026/                                                             ││
│  │       └── 02/                                                           ││
│  │           └── anomalies.json       ← Detected cost spikes               ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                │                                          │
                ▼                                          ▼
    ┌───────────────────┐                    ┌───────────────────┐
    │     DATADOG       │                    │   OUTLOOK/SMTP    │
    │   (Cost Data)     │                    │   (Send Emails)   │
    │                   │                    │                   │
    │  aws.cost.*       │                    │  Team reports     │
    │  84 accounts      │                    │  Admin summary    │
    └───────────────────┘                    └───────────────────┘
```

### Why S3 Instead of MongoDB?

| Feature | MongoDB | S3 |
|---------|---------|-----|
| **Cost** | ~$20-50/month (managed) | ~$0.01-0.10/month |
| **Maintenance** | Backups, scaling, patches | Zero maintenance |
| **Setup** | Install, configure, secure | Just create bucket |
| **Serverless** | Needs connection pooling | Native support |
| **Data access** | Query language | Simple JSON files |
| **Durability** | 99.99% | 99.999999999% (11 9's) |

---

## What You Need (Prerequisites)

### 1. AWS Account & Credentials

You need an IAM user with S3 access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::aws-cost-agent-data",
        "arn:aws:s3:::aws-cost-agent-data/*"
      ]
    }
  ]
}
```

**How to create IAM credentials:**
1. Go to AWS Console → IAM → Users → Create User
2. User name: `cost-agent-service`
3. Attach policy above (or `AmazonS3FullAccess` for testing)
4. Create Access Key → Download CSV
5. Save: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

### 2. Datadog API Keys

| Credential | Where to Get It |
|------------|-----------------|
| **API Key** | Datadog → Organization Settings → API Keys |
| **App Key** | Datadog → Organization Settings → Application Keys |
| **Site** | `datadoghq.com` (US) or `datadoghq.eu` (EU) |

### 3. Email (SMTP) Credentials

For Office 365 / Outlook:

| Setting | Value |
|---------|-------|
| SMTP Host | `smtp.office365.com` |
| SMTP Port | `587` |
| SMTP User | Your email address |
| SMTP Password | Password or App Password |

### 4. Team Mapping Data

List of 84 teams with:
- Team name
- AWS Account ID (12 digits)
- Team email address

---

## Server Requirements

### Do I Need a Server?

**YES** - but simpler than before (no database to manage!)

### Options (Simplest to Most Complex)

| Option | Cost | Best For |
|--------|------|----------|
| **AWS Lambda + EventBridge** | ~$1/month | Serverless, scheduled only |
| **AWS ECS Fargate** | ~$10/month | Container, always-on |
| **EC2 t3.micro** | ~$8/month | Simple VM |
| **Docker on existing server** | $0 extra | If you have infra |

### Minimum Specs (if using EC2/VM)

```
CPU: 1 vCPU
RAM: 512 MB (1 GB recommended)
Storage: 5 GB (code + logs only, data in S3)
OS: Ubuntu 22.04 LTS or Amazon Linux 2
```

### Network Access Required

```
Outbound only:
- s3.amazonaws.com (port 443)
- api.datadoghq.com (port 443)
- smtp.office365.com (port 587)
```

---

## S3 Bucket Structure

The agent automatically creates and manages this structure:

```
aws-cost-agent-data/                    ← Your bucket name
│
├── config/
│   └── notification_config.json        ← Agent settings
│       {
│         "anomaly_threshold": 20.0,
│         "schedule_day": "monday",
│         "schedule_hour": 9,
│         "global_admin_emails": ["admin@company.com"],
│         ...
│       }
│
├── teams/
│   └── teams.json                      ← All 84 teams
│       {
│         "teams": [
│           {"team_name": "Platform", "aws_account_id": "123...", "team_email": "..."},
│           {"team_name": "DevOps", "aws_account_id": "234...", "team_email": "..."},
│           ...
│         ]
│       }
│
├── costs/
│   └── 2026/
│       └── 02/
│           ├── 123456789012.json       ← Cost records per account
│           ├── 234567890123.json
│           └── ...
│
└── anomalies/
    └── 2026/
        └── 02/
            └── anomalies.json          ← All anomalies for the month
```

---

## Step-by-Step Installation

### Option A: Docker (Recommended)

#### Step 1: Create Project Directory

```bash
mkdir -p /opt/aws-cost-agent
cd /opt/aws-cost-agent
```

#### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: cost-agent
    restart: always
    ports:
      - "8001:8001"
    environment:
      # AWS S3 Configuration
      - S3_BUCKET_NAME=${S3_BUCKET_NAME:-aws-cost-agent-data}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      # Datadog Configuration
      - DATADOG_API_KEY=${DATADOG_API_KEY}
      - DATADOG_APP_KEY=${DATADOG_APP_KEY}
      - DATADOG_SITE=${DATADOG_SITE:-datadoghq.com}
      # SMTP Configuration
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SENDER_EMAIL=${SENDER_EMAIL}
```

#### Step 3: Create Dockerfile

```bash
mkdir -p backend
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
EOF
```

#### Step 4: Create requirements.txt

```bash
cat > backend/requirements.txt << 'EOF'
fastapi==0.110.1
uvicorn==0.25.0
python-dotenv>=1.0.1
pydantic>=2.6.4
email-validator>=2.2.0
apscheduler>=3.10.0
httpx>=0.25.0
boto3>=1.34.0
EOF
```

#### Step 5: Copy server.py

Copy the `server.py` file to `backend/server.py`

#### Step 6: Create .env File

```bash
cat > .env << 'EOF'
# AWS S3 Configuration (REQUIRED)
S3_BUCKET_NAME=aws-cost-agent-data
AWS_ACCESS_KEY_ID=AKIA...your-key...
AWS_SECRET_ACCESS_KEY=...your-secret...
AWS_REGION=us-east-1

# Datadog Configuration (REQUIRED for real data)
DATADOG_API_KEY=your_datadog_api_key
DATADOG_APP_KEY=your_datadog_app_key
DATADOG_SITE=datadoghq.com

# SMTP Configuration (REQUIRED for emails)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=aws-notifications@yourcompany.com
SMTP_PASSWORD=your_password
SENDER_EMAIL=aws-notifications@yourcompany.com
EOF

chmod 600 .env
```

#### Step 7: Start the Service

```bash
docker-compose up -d
docker-compose logs -f
```

#### Step 8: Verify

```bash
curl http://localhost:8001/api/health
# Expected: {"status":"healthy","timestamp":"...","storage":"S3"}
```

---

### Option B: AWS Lambda (Serverless)

For Lambda deployment, you'll need to:

1. Package the code with dependencies
2. Create Lambda function
3. Set up EventBridge for weekly schedule
4. Configure environment variables

**Lambda Handler (create `lambda_handler.py`):**

```python
from mangum import Mangum
from server import app

handler = Mangum(app, lifespan="off")
```

**Add to requirements.txt:**
```
mangum>=0.17.0
```

**EventBridge Rule:**
```
cron(0 9 ? * MON *)  # Every Monday at 9:00 UTC
```

---

### Option C: Direct Linux Installation

```bash
# 1. Install Python
sudo apt update
sudo apt install -y python3.11 python3.11-venv

# 2. Create app directory
sudo mkdir -p /opt/aws-cost-agent
cd /opt/aws-cost-agent

# 3. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install fastapi uvicorn python-dotenv pydantic email-validator apscheduler httpx boto3

# 5. Copy server.py and create .env

# 6. Create systemd service
sudo cat > /etc/systemd/system/aws-cost-agent.service << 'EOF'
[Unit]
Description=AWS Cost Notification Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aws-cost-agent
Environment=PATH=/opt/aws-cost-agent/venv/bin
EnvironmentFile=/opt/aws-cost-agent/.env
ExecStart=/opt/aws-cost-agent/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 7. Start service
sudo systemctl daemon-reload
sudo systemctl start aws-cost-agent
sudo systemctl enable aws-cost-agent
```

---

## Configuration Guide

### Set Notification Settings

```bash
API_URL="http://localhost:8001"

curl -X PUT "$API_URL/api/config" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_threshold": 20,
    "schedule_day": "monday",
    "schedule_hour": 9,
    "global_admin_emails": [
      "admin1@yourcompany.com",
      "admin2@yourcompany.com"
    ]
  }'
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `anomaly_threshold` | float | 20.0 | % increase to flag as anomaly |
| `schedule_day` | string | "monday" | Weekly report day |
| `schedule_hour` | int | 9 | Hour in UTC (0-23) |
| `global_admin_emails` | list | [] | Admin emails |

---

## Adding Your 84 Teams

### Method 1: Bulk Upload (Recommended)

Create `teams.json`:

```json
[
  {"team_name": "Platform Team", "aws_account_id": "123456789012", "team_email": "platform@company.com"},
  {"team_name": "DevOps Team", "aws_account_id": "234567890123", "team_email": "devops@company.com"},
  {"team_name": "Data Science", "aws_account_id": "345678901234", "team_email": "datascience@company.com"}
]
```

Upload:

```bash
curl -X POST "$API_URL/api/teams/bulk" \
  -H "Content-Type: application/json" \
  -d @teams.json
```

### Method 2: From CSV

```python
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
```

---

## Testing Everything

### 1. Health Check

```bash
curl "$API_URL/api/health"
```

### 2. Check S3 Storage

```bash
curl "$API_URL/api/storage/info"
```

### 3. Add a Test Team

```bash
curl -X POST "$API_URL/api/teams" \
  -H "Content-Type: application/json" \
  -d '{"team_name":"Test Team","aws_account_id":"999999999999","team_email":"test@company.com"}'
```

### 4. Preview Team Report

```bash
# Get team ID
TEAM_ID=$(curl -s "$API_URL/api/teams" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Preview report
curl "$API_URL/api/preview/team-report/$TEAM_ID"
```

### 5. Preview Admin Report

```bash
curl "$API_URL/api/preview/admin-report"
```

### 6. Trigger Manual Report

```bash
curl -X POST "$API_URL/api/trigger/weekly-report"
```

### 7. Check S3 Bucket (via AWS CLI)

```bash
aws s3 ls s3://aws-cost-agent-data/ --recursive
```

---

## Going Live Checklist

- [ ] AWS credentials configured (S3 access)
- [ ] S3 bucket created (or auto-created by agent)
- [ ] Datadog API keys added
- [ ] SMTP credentials configured
- [ ] All 84 teams imported
- [ ] Admin emails set
- [ ] Test email sent successfully
- [ ] Preview reports look correct
- [ ] Scheduler running (check `/api/scheduler/status`)

---

## Troubleshooting

### "Access Denied" on S3

1. Check IAM policy has correct bucket name
2. Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
3. Check bucket region matches `AWS_REGION`

### "Datadog credentials not configured"

Add to `.env`:
```
DATADOG_API_KEY=your_key
DATADOG_APP_KEY=your_key
```

### "SMTP not configured"

Add to `.env`:
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
SENDER_EMAIL=your@email.com
```

### View Logs

```bash
# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u aws-cost-agent -f
```

---

## API Reference

### Base URL
```
http://your-server:8001/api
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/storage/info` | S3 bucket info |
| GET | `/scheduler/status` | Scheduler status |
| GET | `/teams` | List all teams |
| POST | `/teams` | Create team |
| POST | `/teams/bulk` | Bulk create |
| DELETE | `/teams/{id}` | Delete team |
| GET | `/config` | Get config |
| PUT | `/config` | Update config |
| GET | `/costs/history` | Cost history |
| GET | `/anomalies` | Anomalies list |
| POST | `/trigger/weekly-report` | Trigger report |
| GET | `/preview/team-report/{id}` | Preview team email |
| GET | `/preview/admin-report` | Preview admin email |

---

## Cost Estimate

### Monthly Costs

| Resource | Cost |
|----------|------|
| S3 Storage (< 1 GB) | ~$0.02 |
| S3 Requests (~10k/month) | ~$0.01 |
| EC2 t3.micro (if used) | ~$8.00 |
| **Total (with EC2)** | **~$8.03** |
| **Total (Lambda only)** | **~$0.10** |

Compare to MongoDB Atlas: $20-50/month

---

## Security Best Practices

1. **Never commit `.env` to git**
2. **Use IAM roles on EC2** instead of access keys
3. **Enable S3 bucket encryption**
4. **Restrict S3 bucket access** to agent only
5. **Use secrets manager** for production credentials

---

## File Structure

```
/opt/aws-cost-agent/
├── docker-compose.yml
├── .env                    ← Secrets (chmod 600)
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── server.py           ← Main application
```

Data is stored in S3, not on the server!
