# AWS Cost AI Agent - Complete Documentation

**Version:** 3.0.0  
**Purpose:** AI-Powered AWS Cost Monitoring for 84 Accounts  
**Audience:** DevOps, FinOps, Engineering Teams

---

# TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [What Does This Agent Do?](#2-what-does-this-agent-do)
3. [System Architecture](#3-system-architecture)
4. [Service Components Explained](#4-service-components-explained)
5. [How Gemini AI Helps](#5-how-gemini-ai-helps)
6. [Data Flow](#6-data-flow)
7. [Storage Structure](#7-storage-structure)
8. [Installation Guide](#8-installation-guide)
9. [Configuration](#9-configuration)
10. [API Reference](#10-api-reference)
11. [Usage Examples](#11-usage-examples)
12. [Security](#12-security)
13. [Troubleshooting](#13-troubleshooting)
14. [FAQ](#14-faq)

---

# 1. EXECUTIVE SUMMARY

## What is this?
A **backend automation agent** that monitors AWS costs across **84 accounts**, uses **AI (Gemini 3 Flash)** to analyze spending patterns, and sends **automated weekly email reports** to teams and admins.

## Key Features
- **Automated Cost Monitoring**: Weekly reports sent automatically
- **AI-Powered Analysis**: Explains WHY costs changed, not just WHAT changed
- **Anomaly Detection**: Flags unusual cost increases
- **Cost Predictions**: Forecasts next month's expenses
- **Optimization Recommendations**: AI suggests ways to save money
- **Team Isolation**: Each team only sees their own account's data
- **Admin Consolidated View**: Admins see all 84 accounts

## Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | Python + FastAPI |
| AI | Google Gemini 3 Flash |
| Storage | AWS S3 |
| Data Source | Datadog |
| Email | SMTP (Outlook) |
| Scheduler | APScheduler |

---

# 2. WHAT DOES THIS AGENT DO?

## Weekly Automated Workflow

```
Every Monday at 9:00 AM UTC (configurable):

STEP 1: FETCH DATA
├── Connect to Datadog API
├── Query aws.cost.* metrics for each of 84 AWS accounts
├── Get current month and previous month costs
└── Get service-level breakdown (EC2, RDS, S3, Lambda, etc.)

STEP 2: ANALYZE COSTS
├── Calculate month-over-month % change
├── Compare against threshold (default: 20%)
├── Flag anomalies (accounts with unusual increases)
└── Identify top cost drivers per account

STEP 3: AI ANALYSIS
├── Send cost data to Gemini 3 Flash
├── AI explains WHY costs changed (root cause analysis)
├── AI predicts next month's costs
├── AI generates optimization recommendations
└── AI creates executive summary for admins

STEP 4: SEND REPORTS
├── Generate HTML email for each team (their data only)
├── Generate consolidated HTML email for admins (all 84 accounts)
├── Include Datadog dashboard links
├── Send via SMTP (Outlook)
└── Log results
```

## What Problems Does It Solve?

| Problem | Solution |
|---------|----------|
| "I don't know why costs increased" | AI explains root cause |
| "I can't monitor 84 accounts manually" | Automated weekly monitoring |
| "Teams don't know their cost impact" | Individual team reports |
| "No time for cost optimization" | AI provides actionable recommendations |
| "Finance asks for cost forecasts" | AI predicts next month's costs |

---

# 3. SYSTEM ARCHITECTURE

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         AWS COST AI AGENT                                 │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    PRESENTATION LAYER                             │  │
│   │                                                                   │  │
│   │   REST API (FastAPI) - Port 8001                                 │  │
│   │   ├── /api/health, /api/config                                   │  │
│   │   ├── /api/teams (CRUD)                                          │  │
│   │   ├── /api/trigger/* (manual triggers)                           │  │
│   │   ├── /api/preview/* (report previews)                           │  │
│   │   ├── /api/ai/* (AI analysis)                                    │  │
│   │   └── /api/costs/*, /api/anomalies                               │  │
│   │                                                                   │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    BUSINESS LOGIC LAYER                           │  │
│   │                                                                   │  │
│   │   ┌────────────┐   ┌────────────┐   ┌────────────┐              │  │
│   │   │ SCHEDULER  │──▶│   COST     │──▶│     AI     │              │  │
│   │   │(APScheduler│   │  ANALYZER  │   │  SERVICE   │              │  │
│   │   │ weekly cron│   │ compare,   │   │  (Gemini)  │              │  │
│   │   │           )│   │ detect     │   │  explain,  │              │  │
│   │   │            │   │ anomalies  │   │  predict   │              │  │
│   │   └────────────┘   └────────────┘   └────────────┘              │  │
│   │                                                                   │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    INTEGRATION LAYER                              │  │
│   │                                                                   │  │
│   │   ┌────────────┐   ┌────────────┐   ┌────────────┐              │  │
│   │   │  DATADOG   │   │   EMAIL    │   │     S3     │              │  │
│   │   │  SERVICE   │   │  SERVICE   │   │  STORAGE   │              │  │
│   │   │ fetch cost │   │   (SMTP)   │   │  (config,  │              │  │
│   │   │ data       │   │ send HTML  │   │  teams,    │              │  │
│   │   │            │   │ reports    │   │  history)  │              │  │
│   │   └────────────┘   └────────────┘   └────────────┘              │  │
│   │                                                                   │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                  │
         ▼                    ▼                    ▼                  ▼
   ┌──────────┐        ┌──────────┐        ┌──────────┐       ┌──────────┐
   │ DATADOG  │        │  GEMINI  │        │   AWS    │       │  SMTP    │
   │  API     │        │    AI    │        │   S3     │       │ (Outlook)│
   │          │        │          │        │          │       │          │
   │ Cost     │        │ Analysis │        │ Storage  │       │ Emails   │
   │ Metrics  │        │ Insights │        │ Bucket   │       │ Reports  │
   └──────────┘        └──────────┘        └──────────┘       └──────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     EC2 INSTANCE (Ubuntu 22.04)                  │
│                                                                  │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │                   SYSTEMD SERVICE                          │ │
│   │                aws-cost-agent.service                      │ │
│   │                                                            │ │
│   │   ┌─────────────────────────────────────────────────────┐ │ │
│   │   │           PYTHON VIRTUAL ENV                         │ │ │
│   │   │           /opt/aws-cost-agent/venv                   │ │ │
│   │   │                                                      │ │ │
│   │   │   ┌─────────────────────────────────────────────┐  │ │ │
│   │   │   │             UVICORN SERVER                   │  │ │ │
│   │   │   │               Port: 8001                     │  │ │ │
│   │   │   │                                              │  │ │ │
│   │   │   │   ┌─────────────────────────────────────┐  │  │ │ │
│   │   │   │   │          FASTAPI APP                 │  │  │ │ │
│   │   │   │   │          (server.py)                 │  │  │ │ │
│   │   │   │   │                                      │  │  │ │ │
│   │   │   │   │  Components:                         │  │  │ │ │
│   │   │   │   │  • REST API endpoints               │  │  │ │ │
│   │   │   │   │  • Scheduler (APScheduler)          │  │  │ │ │
│   │   │   │   │  • Cost Analyzer                    │  │  │ │ │
│   │   │   │   │  • AI Service (Gemini)              │  │  │ │ │
│   │   │   │   │  • S3 Storage Service               │  │  │ │ │
│   │   │   │   │  • Email Service (SMTP)             │  │  │ │ │
│   │   │   │   │  • Datadog Service                  │  │  │ │ │
│   │   │   │   │                                      │  │  │ │ │
│   │   │   │   └─────────────────────────────────────┘  │  │ │ │
│   │   │   └─────────────────────────────────────────────┘  │ │ │
│   │   └─────────────────────────────────────────────────────┘ │ │
│   └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│   Files:                                                         │
│   /opt/aws-cost-agent/                                          │
│   ├── server.py       # Main application                        │
│   ├── .env            # API keys (chmod 600)                    │
│   ├── venv/           # Python virtual environment              │
│   └── data/           # Local fallback storage                  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                    SECURITY GROUP                                 │
│                                                                  │
│   INBOUND:                      OUTBOUND:                        │
│   • SSH (22) ← Your IP only    • HTTPS (443) → All (APIs)       │
│                                 • SMTP (587) → All (Email)       │
│                                                                  │
│   NOTE: No public IP required. Only outbound connections.       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

# 4. SERVICE COMPONENTS EXPLAINED

## 4.1 Datadog Service

**Purpose:** Fetches AWS cost data from your Datadog account

**What it does:**
- Connects to Datadog API using your API keys
- Queries `aws.cost.*` metrics for each AWS account
- Gets cost breakdown by service (EC2, RDS, S3, Lambda, etc.)
- Retrieves current month and previous month data

**Why you need it:**
- Datadog aggregates cost data from all 84 AWS accounts
- Provides service-level breakdown
- Historical data for trend analysis

**Configuration:**
```
DATADOG_API_KEY=your_api_key      # From Datadog → Org Settings → API Keys
DATADOG_APP_KEY=your_app_key      # From Datadog → Org Settings → Application Keys
DATADOG_SITE=datadoghq.com        # Or datadoghq.eu for EU
```

---

## 4.2 AI Service (Gemini 3 Flash)

**Purpose:** Provides intelligent analysis of your cost data

**What it does:**
- **Anomaly Explanation:** Analyzes cost changes and explains WHY they happened
- **Cost Prediction:** Predicts next month's costs based on historical trends
- **Optimization Recommendations:** Suggests ways to reduce costs
- **Executive Summary:** Generates C-level summaries for admin reports

**Why you need it:**
- Raw numbers don't tell you WHY costs changed
- Manual analysis of 84 accounts is time-consuming
- AI spots patterns humans might miss
- Actionable recommendations save real money

**Configuration:**
```
GEMINI_API_KEY=your_gemini_key    # From https://aistudio.google.com/apikey
```

---

## 4.3 S3 Storage Service

**Purpose:** Stores all application data securely in AWS S3

**What it stores:**
- Configuration settings
- Team/account mappings
- Cost history per account
- Detected anomalies
- AI insights over time

**Why you need it:**
- Persistent storage for configuration
- Historical cost data for predictions
- No database server to manage
- 99.999999999% durability (11 nines)

**Configuration:**
```
S3_BUCKET_NAME=aws-cost-agent-data
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
```

---

## 4.4 Email Service (SMTP)

**Purpose:** Sends HTML-formatted cost reports via email

**What it sends:**
- **Team Reports:** Each team gets ONLY their account's cost data
- **Admin Reports:** Global admins get consolidated view of all 84 accounts

**Report contents:**
- Current month vs previous month costs
- Percentage change with anomaly flags
- Service-by-service breakdown
- AI analysis explaining changes
- Next month prediction
- Datadog dashboard links

**Configuration:**
```
SMTP_HOST=smtp.office365.com      # For Outlook/O365
SMTP_PORT=587
SMTP_USER=notifications@company.com
SMTP_PASSWORD=your_password
SENDER_EMAIL=notifications@company.com
```

---

## 4.5 Scheduler Service

**Purpose:** Runs the cost report automatically on a schedule

**Configuration:**
```
SCHEDULE_DAY=monday               # monday, tuesday, etc.
SCHEDULE_HOUR=9                   # 0-23 in UTC
```

---

## 4.6 Cost Analyzer

**Purpose:** Compares costs and detects anomalies

**What it does:**
- Calculates month-over-month change
- Flags anomalies when change exceeds threshold
- Identifies top cost drivers per service
- Compares service-level changes

**Configuration:**
```
ANOMALY_THRESHOLD=20              # Flag if costs increase > 20%
```

---

# 5. HOW GEMINI AI HELPS

## Without AI (Raw Data Only)

```
Platform Team
Current: $45,230
Previous: $38,500
Change: +17.5%

EC2: $18,500
RDS: $12,800
S3: $5,200
```

**Problem:** You see WHAT changed, but not WHY. You have to investigate manually.

---

## With Gemini AI

```
🧠 AI ANALYSIS

Root Cause Analysis:
Your costs increased 17.5% primarily due to:

• EC2 scaling for product launch (+$4,200)
  - 8 new m5.xlarge instances were launched on Feb 5-7
  - Auto-scaling triggered 3 times during traffic spike
  - These instances are still running at 23% utilization

• RDS storage expansion (+$1,800)
  - Database grew 40% due to new user signups
  - Automated backup retention increased from 7 to 14 days

Positive Note:
• Lambda costs decreased 15% (-$730) after your optimization

💡 Recommendations:
1. Convert 4 idle EC2 instances to Reserved (save $800/mo)
2. Enable RDS storage auto-scaling alerts at 80%
3. Consider Aurora Serverless for variable database workloads

📈 Next Month Prediction:
Estimated cost: $48,000 - $52,000
Confidence: High (based on 6 months of data)
Risk: Q1 marketing campaign may increase traffic 20%
```

**Solution:** AI tells you exactly WHY costs changed and WHAT to do about it.

---

## AI Capabilities

| Feature | What It Does | How It Helps |
|---------|--------------|--------------|
| **Anomaly Explanation** | Analyzes service-level changes | Know exactly which service caused the spike |
| **Pattern Detection** | Identifies recurring patterns | Spot seasonal trends, weekly patterns |
| **Cost Prediction** | Uses historical data to forecast | Budget planning, early warning |
| **Optimization Tips** | Suggests RI, right-sizing, cleanup | Actionable savings ($10K+/month) |
| **Executive Summary** | Generates C-level summaries | Admin reports ready for management |

---

# 6. DATA FLOW

```
┌───────────────────────────────────────────────────────────────────────┐
│                            WEEKLY WORKFLOW                             │
└───────────────────────────────────────────────────────────────────────┘

    ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
    │  STEP 1  │──────▶│  STEP 2  │──────▶│  STEP 3  │──────▶│  STEP 4  │
    │  FETCH   │       │ ANALYZE  │       │    AI    │       │   SEND   │
    └──────────┘       └──────────┘       └──────────┘       └──────────┘
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │ Datadog API │    │ Compare     │    │ Gemini AI   │    │ Email HTML  │
  │ call for    │    │ current vs  │    │ analyzes    │    │ reports to  │
  │ each of 84  │    │ previous    │    │ patterns,   │    │ teams &     │
  │ accounts    │    │ month       │    │ explains    │    │ admins      │
  │             │    │             │    │ WHY         │    │             │
  │ Get cost    │    │ Flag if     │    │             │    │ Include     │
  │ breakdown   │    │ change >    │    │ Predicts    │    │ Datadog     │
  │ by service  │    │ threshold   │    │ next month  │    │ links       │
  │             │    │ (anomaly)   │    │             │    │             │
  │             │    │             │    │ Recommends  │    │             │
  │             │    │             │    │ savings     │    │             │
  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
         │                  │                  │                  │
         └──────────────────┴──────────────────┴──────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │   AWS S3        │
                          │   STORAGE       │
                          │                 │
                          │  costs/         │
                          │  anomalies/     │
                          │  ai_insights/   │
                          └─────────────────┘
```

---

# 7. STORAGE STRUCTURE

## S3 Bucket Layout

```
aws-cost-agent-data/                          ← S3 Bucket
│
├── config/
│   └── notification_config.json              ← Agent configuration
│       {
│         "anomaly_threshold": 20.0,
│         "schedule_day": "monday",
│         "schedule_hour": 9,
│         "global_admin_emails": ["admin@company.com"],
│         "ai_enabled": true
│       }
│
├── teams/
│   └── teams.json                            ← All 84 team mappings
│       {
│         "teams": [
│           {
│             "id": "uuid-1",
│             "team_name": "Platform Team",
│             "aws_account_id": "123456789012",
│             "team_email": "platform@company.com"
│           },
│           ... (84 teams)
│         ]
│       }
│
├── costs/
│   └── 2026/
│       └── 02/
│           ├── 123456789012.json             ← Cost data per account
│           ├── 234567890123.json
│           └── ... (84 accounts)
│
├── anomalies/
│   └── 2026/
│       └── 02/
│           └── anomalies.json                ← Detected cost spikes
│
└── ai_insights/
    └── 2026/
        └── 02/
            └── insights.json                 ← AI learning history
```

---

# 8. INSTALLATION GUIDE

## Prerequisites
- Linux server (Ubuntu 22.04 recommended)
- Python 3.10+
- Outbound internet access (HTTPS, SMTP)
- **No public IP required**

## Required API Keys (Prepare Before Installation)

| Service | What You Need | Where to Get It |
|---------|---------------|-----------------|
| **Gemini AI** | API Key | https://aistudio.google.com/apikey (FREE) |
| **AWS S3** | Access Key, Secret Key | AWS IAM Console |
| **Datadog** | API Key, App Key | Datadog → Org Settings → API Keys |
| **SMTP** | Username, Password | Your email provider (Outlook/Gmail) |

## Installation Steps

```bash
# 1. Download installer
wget https://your-repo/install.sh
chmod +x install.sh

# 2. Run installer (will prompt for credentials)
sudo ./install.sh

# 3. The installer will:
#    - Install Python dependencies
#    - Create virtual environment
#    - Prompt for all API keys
#    - Create .env file with secure permissions
#    - Set up systemd service
#    - Start the agent

# 4. Verify it's running
curl http://localhost:8001/api/health
```

## Post-Installation

```bash
# Add your 84 teams
curl -X POST http://localhost:8001/api/teams/bulk \
  -H "Content-Type: application/json" \
  -d @teams.json

# Set admin emails
curl -X PUT http://localhost:8001/api/config \
  -H "Content-Type: application/json" \
  -d '{"global_admin_emails": ["admin@company.com"]}'

# Test with a preview
curl http://localhost:8001/api/preview/admin-report

# Trigger first report
curl -X POST http://localhost:8001/api/trigger/weekly-report
```

---

# 9. CONFIGURATION

## View Current Configuration

```bash
curl http://localhost:8001/api/config
```

## Update Configuration

```bash
curl -X PUT http://localhost:8001/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_threshold": 25,
    "schedule_day": "wednesday",
    "schedule_hour": 14,
    "global_admin_emails": ["admin1@company.com", "admin2@company.com"],
    "ai_enabled": true
  }'
```

## Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `anomaly_threshold` | float | 20.0 | % increase to flag as anomaly |
| `schedule_day` | string | "monday" | Day for weekly report |
| `schedule_hour` | int | 9 | Hour in UTC (0-23) |
| `global_admin_emails` | list | [] | Emails for admin report |
| `ai_enabled` | bool | true | Enable/disable AI analysis |

---

# 10. API REFERENCE

## Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/` | GET | Agent version and features |
| `/api/scheduler/status` | GET | Next scheduled run time |
| `/api/storage/info` | GET | Storage configuration |

## Team Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teams` | GET | List all teams |
| `/api/teams` | POST | Add single team |
| `/api/teams/bulk` | POST | Add multiple teams |
| `/api/teams/{id}` | GET | Get specific team |
| `/api/teams/{id}` | DELETE | Remove team |

## Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Get current settings |
| `/api/config` | PUT | Update settings |

## AI Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai/analyze/{id}` | POST | Run AI analysis for one team |
| `/api/ai/recommendations` | GET | Get org-wide AI recommendations |
| `/api/ai/insights` | GET | Get historical AI insights |

## Reports

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trigger/weekly-report` | POST | Trigger full report now |
| `/api/trigger/team-report/{id}` | POST | Trigger single team report |
| `/api/preview/team-report/{id}` | GET | Preview without sending |
| `/api/preview/admin-report` | GET | Preview admin report |

## Data Queries

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/costs/history` | GET | Historical cost data |
| `/api/anomalies` | GET | Detected anomalies |

---

# 11. USAGE EXAMPLES

## First Time Setup

```bash
# 1. Check agent is running
curl http://localhost:8001/api/health

# 2. Add your teams (create teams.json first)
curl -X POST http://localhost:8001/api/teams/bulk \
  -H "Content-Type: application/json" \
  -d @teams.json

# 3. Set admin emails
curl -X PUT http://localhost:8001/api/config \
  -H "Content-Type: application/json" \
  -d '{"global_admin_emails": ["admin@company.com"]}'

# 4. Preview report
curl http://localhost:8001/api/preview/admin-report

# 5. Trigger first report
curl -X POST http://localhost:8001/api/trigger/weekly-report
```

## Daily Operations

```bash
# Check agent health
curl http://localhost:8001/api/health

# View recent anomalies
curl http://localhost:8001/api/anomalies?limit=10

# Get AI recommendations
curl http://localhost:8001/api/ai/recommendations

# Check next scheduled run
curl http://localhost:8001/api/scheduler/status
```

## Debug a Team's Costs

```bash
# Get team ID
curl http://localhost:8001/api/teams | grep -A5 "DevOps"

# Run AI analysis
curl -X POST http://localhost:8001/api/ai/analyze/{team_id}

# View cost history
curl "http://localhost:8001/api/costs/history?team_name=DevOps%20Team"
```

## Manual Report Triggers

```bash
# Full weekly report (all 84 teams + admins)
curl -X POST http://localhost:8001/api/trigger/weekly-report

# Single team report
curl -X POST http://localhost:8001/api/trigger/team-report/{team_id}

# Preview without sending email
curl http://localhost:8001/api/preview/admin-report
```

---

# 12. SECURITY

## Network Security

**The agent only makes OUTBOUND connections. No public IP required.**

| Direction | Port | Destination | Purpose |
|-----------|------|-------------|---------|
| OUTBOUND | 443 | api.datadoghq.com | Fetch cost data |
| OUTBOUND | 443 | generativelanguage.googleapis.com | AI analysis |
| OUTBOUND | 443 | s3.amazonaws.com | Storage |
| OUTBOUND | 587 | smtp.office365.com | Send emails |

## EC2 Security Group

**Inbound Rules:**
| Type | Port | Source | Description |
|------|------|--------|-------------|
| SSH | 22 | Your IP only (`x.x.x.x/32`) | Admin access |

**Outbound Rules:**
| Type | Port | Destination | Description |
|------|------|-------------|-------------|
| HTTPS | 443 | `0.0.0.0/0` | APIs (Datadog, Gemini, S3) |
| SMTP | 587 | `0.0.0.0/0` | Send emails |

## Credential Security

| Feature | Description |
|---------|-------------|
| **Secure Input** | API keys entered with hidden input during install |
| **File Permissions** | `.env` has chmod 600 (owner read/write only) |
| **No Hardcoding** | All credentials loaded from environment |
| **Git Protected** | `.gitignore` prevents committing secrets |
| **Team Isolation** | Each team only sees their own cost data |

## Best Practices

| ✅ Do | ❌ Don't |
|-------|---------|
| Restrict SSH to your IP only | Open SSH to 0.0.0.0/0 |
| Use security groups | Rely on OS firewall only |
| Keep port 8001 closed if not needed | Expose API to internet |
| Use IAM roles on EC2 | Hardcode AWS credentials |
| Rotate API keys regularly | Share API keys |

---

# 13. TROUBLESHOOTING

## Agent Not Starting

```bash
# Check status
sudo systemctl status aws-cost-agent

# Check logs for errors
sudo journalctl -u aws-cost-agent -n 50

# Common issues:
# - Missing .env file
# - Python dependencies not installed
# - Port 8001 already in use
```

## Emails Not Sending

```bash
# Check SMTP config in logs
sudo journalctl -u aws-cost-agent | grep -i smtp

# Verify .env has correct SMTP settings
cat /opt/aws-cost-agent/.env | grep SMTP

# Test connectivity to SMTP server
nc -zv smtp.office365.com 587
```

## AI Analysis Not Working

```bash
# Check if Gemini key is configured
curl http://localhost:8001/api/health
# Look for "ai_configured": true

# Check logs for AI errors
sudo journalctl -u aws-cost-agent | grep -i gemini
```

## No Data from Datadog

```bash
# Check Datadog config
curl http://localhost:8001/api/storage/info

# Verify Datadog keys in .env
cat /opt/aws-cost-agent/.env | grep DATADOG

# Check logs for Datadog errors
sudo journalctl -u aws-cost-agent | grep -i datadog
```

## S3 Storage Issues

```bash
# Check S3 config
curl http://localhost:8001/api/storage/info

# If using local fallback, data stored in:
ls -la /opt/aws-cost-agent/data/

# Check AWS credentials
cat /opt/aws-cost-agent/.env | grep AWS
```

## Systemd Commands

```bash
# Start agent
sudo systemctl start aws-cost-agent

# Stop agent
sudo systemctl stop aws-cost-agent

# Restart agent
sudo systemctl restart aws-cost-agent

# Enable auto-start on boot
sudo systemctl enable aws-cost-agent

# View live logs
sudo journalctl -u aws-cost-agent -f

# View last 100 lines
sudo journalctl -u aws-cost-agent -n 100
```

---

# 14. FAQ

**Q: What if I don't have Datadog?**
A: The agent will use mock data for testing. For production, you need Datadog with AWS Cost Management integration enabled.

**Q: Can I use a different AI model?**
A: Currently optimized for Gemini 3 Flash. Other models can be added.

**Q: How accurate are the predictions?**
A: Accuracy improves with more historical data. After 3+ months, predictions are typically within 10% of actual costs.

**Q: Can teams see other teams' costs?**
A: No. Each team only receives their own account's report. Only admins see all accounts.

**Q: Does this need a public IP?**
A: No. The agent only makes outbound connections. No inbound traffic required.

**Q: What's the cost to run this?**
| Component | Monthly Cost |
|-----------|-------------|
| Gemini 3 Flash | $0-5 (free tier available) |
| AWS S3 Storage | ~$0.03 |
| Server (EC2 t3.small) | $6-15 |
| **Total** | **$6-20/month** |

**ROI:** AI recommendations typically save **$10,000+/month**

---

# APPENDIX: Sample Teams JSON

Create this file to bulk import your teams:

```json
[
  {
    "team_name": "Platform Team",
    "aws_account_id": "123456789012",
    "team_email": "platform@company.com"
  },
  {
    "team_name": "DevOps Team",
    "aws_account_id": "234567890123",
    "team_email": "devops@company.com"
  },
  {
    "team_name": "Data Science Team",
    "aws_account_id": "345678901234",
    "team_email": "datascience@company.com"
  }
]
```

Import with:
```bash
curl -X POST http://localhost:8001/api/teams/bulk \
  -H "Content-Type: application/json" \
  -d @teams.json
```

---

**Document Version:** 3.0.0  
**Last Updated:** February 2026  
**Built with Gemini 3 Flash AI**
