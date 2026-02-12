# AWS Cost AI Agent 🤖

## AI-Powered AWS Cost Monitoring & Optimization

An intelligent automation agent that learns your AWS cost patterns, predicts future costs, detects anomalies, and provides optimization recommendations using **Gemini 3 Flash AI**.

---

## 🎯 What It Does

| Feature | Description |
|---------|-------------|
| **🔍 Anomaly Detection** | AI explains WHY costs changed |
| **📈 Cost Prediction** | Predicts next month's costs based on trends |
| **💡 Optimization Tips** | AI-generated recommendations to save money |
| **📊 Datadog Integration** | Links directly to your Datadog dashboards |
| **📧 Smart Reports** | AI-powered weekly email reports |
| **🏢 84 Teams Support** | Each team sees only their costs |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AWS COST AI AGENT v3.0                              │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                           INTELLIGENCE LAYER                                │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │ │
│  │  │  GEMINI 3 FLASH │  │  COST ANALYZER  │  │  PREDICTION     │            │ │
│  │  │  AI ENGINE      │  │                 │  │  ENGINE         │            │ │
│  │  │                 │  │  • Compare MoM  │  │                 │            │ │
│  │  │  • Why costs ↑  │  │  • Detect spike │  │  • Forecast $   │            │ │
│  │  │  • Optimize $   │  │  • Flag anomaly │  │  • Trend learn  │            │ │
│  │  │  • Exec summary │  │  • Service drill│  │  • Risk assess  │            │ │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │ │
│  │           │                    │                    │                      │ │
│  │           └────────────────────┼────────────────────┘                      │ │
│  │                                │                                           │ │
│  └────────────────────────────────┼───────────────────────────────────────────┘ │
│                                   │                                              │
│  ┌────────────────────────────────┼───────────────────────────────────────────┐ │
│  │                          DATA LAYER                                         │ │
│  │                                │                                            │ │
│  │  ┌─────────────────┐  ┌───────┴───────┐  ┌─────────────────┐              │ │
│  │  │    DATADOG      │  │   SCHEDULER   │  │   EMAIL SENDER  │              │ │
│  │  │                 │  │               │  │                 │              │ │
│  │  │  aws.cost.*     │──│  Weekly cron  │──│  Team reports   │              │ │
│  │  │  84 accounts    │  │  Configurable │  │  Admin summary  │              │ │
│  │  │  Service data   │  │  Mon-Sun, UTC │  │  AI insights    │              │ │
│  │  └─────────────────┘  └───────────────┘  └─────────────────┘              │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                   │                                              │
│                                   ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                          AWS S3 STORAGE                                     │ │
│  │                                                                             │ │
│  │   📁 config/                    📁 teams/                                  │ │
│  │   └── notification_config.json  └── teams.json (84 teams)                  │ │
│  │                                                                             │ │
│  │   📁 costs/{year}/{month}/      📁 anomalies/{year}/{month}/               │ │
│  │   └── {account_id}.json         └── anomalies.json                         │ │
│  │                                                                             │ │
│  │   📁 ai_insights/{year}/{month}/                                           │ │
│  │   └── insights.json  ← AI learns from historical data                      │ │
│  │                                                                             │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                    │                                      │
                    ▼                                      ▼
        ┌───────────────────┐                  ┌───────────────────┐
        │      DATADOG      │                  │   OUTLOOK/SMTP    │
        │                   │                  │                   │
        │   Cost metrics    │                  │   📧 Team: Own $  │
        │   Service data    │                  │   📧 Admin: All $ │
        │   84 AWS accounts │                  │   🤖 AI insights  │
        │                   │                  │   📊 DD links     │
        └───────────────────┘                  └───────────────────┘
```

---

## ⚡ 1-Step Installation

### Prerequisites
- A Linux server (Ubuntu 22.04 recommended) or Docker
- Your API keys ready (see below)

### Quick Install Script

**Copy and run this single command:**

```bash
curl -sSL https://raw.githubusercontent.com/your-repo/aws-cost-agent/main/install.sh | bash
```

**Or manually:**

```bash
# 1. Create directory and download files
mkdir -p /opt/aws-cost-agent && cd /opt/aws-cost-agent

# 2. Create docker-compose.yml
cat > docker-compose.yml << 'DOCKER_EOF'
version: '3.8'
services:
  cost-agent:
    image: python:3.11-slim
    container_name: aws-cost-ai-agent
    restart: always
    ports:
      - "8001:8001"
    volumes:
      - ./backend:/app/backend
      - ./data:/app/backend/data
    working_dir: /app/backend
    command: >
      bash -c "pip install -q fastapi uvicorn python-dotenv pydantic email-validator 
      apscheduler httpx boto3 emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ 
      && uvicorn server:app --host 0.0.0.0 --port 8001"
    environment:
      - S3_BUCKET_NAME=${S3_BUCKET_NAME:-aws-cost-agent-data}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DATADOG_API_KEY=${DATADOG_API_KEY}
      - DATADOG_APP_KEY=${DATADOG_APP_KEY}
      - DATADOG_SITE=${DATADOG_SITE:-datadoghq.com}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SENDER_EMAIL=${SENDER_EMAIL}
DOCKER_EOF

# 3. Create .env file (EDIT THIS WITH YOUR KEYS!)
cat > .env << 'ENV_EOF'
# === REQUIRED: AI Configuration ===
GEMINI_API_KEY=your_gemini_api_key_here

# === REQUIRED: AWS S3 Storage ===
S3_BUCKET_NAME=aws-cost-agent-data
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# === REQUIRED: Datadog ===
DATADOG_API_KEY=your_datadog_api_key
DATADOG_APP_KEY=your_datadog_app_key
DATADOG_SITE=datadoghq.com

# === REQUIRED: Email (Outlook) ===
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your_password
SENDER_EMAIL=your-email@company.com
ENV_EOF

# 4. Download server.py (or copy from this repo)
mkdir -p backend
curl -o backend/server.py https://your-repo-url/server.py

# 5. Start the agent!
docker-compose up -d

# 6. Verify it's running
curl http://localhost:8001/api/health
```

---

## 🔑 API Keys You Need

| Key | Where to Get | Purpose |
|-----|-------------|---------|
| **GEMINI_API_KEY** | [Google AI Studio](https://aistudio.google.com/apikey) | AI analysis & predictions |
| **AWS_ACCESS_KEY_ID** | AWS IAM Console | S3 storage access |
| **AWS_SECRET_ACCESS_KEY** | AWS IAM Console | S3 storage access |
| **DATADOG_API_KEY** | Datadog → Org Settings → API Keys | Fetch cost data |
| **DATADOG_APP_KEY** | Datadog → Org Settings → App Keys | Fetch cost data |
| **SMTP_USER/PASSWORD** | Your Outlook/O365 account | Send email reports |

### Getting Gemini API Key (Free!)

1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key to your `.env` file

---

## 📊 AI Features in Detail

### 1. Anomaly Explanation
The AI analyzes cost changes and explains WHY:

```
🧠 AI Analysis:
• EC2 costs increased 45% due to new m5.xlarge instances launched on Feb 5
• RDS spike caused by automated snapshot retention increase
• Recommendation: Consider Reserved Instances for stable EC2 workloads
```

### 2. Cost Prediction
Based on historical data, predicts next month:

```
📈 Prediction:
• Estimated next month cost: $45,000 - $52,000
• Confidence: High (based on 6 months of data)
• Risk factors: Potential Q1 traffic surge, new feature launch
```

### 3. Optimization Recommendations
Organization-wide savings opportunities:

```
💡 Recommendations:
1. Convert 12 EC2 instances to Reserved (save ~$8,000/mo)
2. Enable S3 Intelligent-Tiering (save ~$2,000/mo)
3. Right-size 8 over-provisioned RDS instances
4. Delete 45 unattached EBS volumes ($500/mo)
```

### 4. Datadog Links
Every report includes direct links:
- Cost Dashboard
- Cost Explorer (filtered by account)
- Service Breakdown
- Anomaly Monitors

---

## 📧 Email Report Examples

### Team Report
```
🤖 AI-Powered Cost Report
Platform Team - February 2026

Current Month: $45,230
Previous Month: $38,500
Change: +17.5%

🧠 AI Analysis:
Your costs increased primarily due to EC2 scaling for the 
product launch. Lambda costs decreased 15% after optimization.

📊 Datadog Links: [Dashboard] [Explorer] [Breakdown]

Service Breakdown:
• EC2: $18,000 (+25%)
• RDS: $12,500 (+5%)
• Lambda: $8,200 (-15%)
...
```

### Admin Report
```
🤖 AI Organization Summary
All 84 Accounts - February 2026

🧠 Executive Summary (AI):
Total AWS spend reached $1.2M this month, up 8% from January.
12 accounts showed unusual cost patterns. Top concern: DevOps
team's 45% spike requires immediate attention.

⚠️ Top Anomalies: 12 detected
💡 AI Recommendations:
1. Implement Reserved Instances (save $80K/year)
2. Review DevOps account EC2 usage
...
```

---

## 🛠️ API Reference

### Health & Status
```bash
GET /api/health          # Health check + AI status
GET /api/                 # Agent info
GET /api/scheduler/status # Next run time
```

### Teams
```bash
GET    /api/teams         # List all teams
POST   /api/teams         # Create team
POST   /api/teams/bulk    # Bulk create
DELETE /api/teams/{id}    # Delete team
```

### AI Endpoints
```bash
GET  /api/ai/insights                # Historical AI insights
POST /api/ai/analyze/{team_id}       # Run AI analysis for team
GET  /api/ai/recommendations         # Org-wide recommendations
```

### Reports
```bash
POST /api/trigger/weekly-report      # Trigger full report
GET  /api/preview/team-report/{id}   # Preview team email
GET  /api/preview/admin-report       # Preview admin email
```

---

## 📁 Data Storage Structure

```
S3 Bucket: aws-cost-agent-data/
│
├── config/
│   └── notification_config.json     ← Settings
│
├── teams/
│   └── teams.json                   ← 84 team mappings
│
├── costs/2026/02/
│   ├── 123456789012.json           ← Team cost data
│   ├── 234567890123.json
│   └── ...
│
├── anomalies/2026/02/
│   └── anomalies.json              ← Detected anomalies
│
└── ai_insights/2026/02/
    └── insights.json               ← AI learns over time
```

---

## 🔧 Configuration

```bash
# Set anomaly threshold and schedule
curl -X PUT "http://localhost:8001/api/config" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_threshold": 20,
    "schedule_day": "monday",
    "schedule_hour": 9,
    "global_admin_emails": ["admin@company.com"],
    "ai_enabled": true
  }'
```

---

## 🚀 Add Your 84 Teams

```bash
# Bulk upload teams
curl -X POST "http://localhost:8001/api/teams/bulk" \
  -H "Content-Type: application/json" \
  -d '[
    {"team_name": "Platform", "aws_account_id": "111111111111", "team_email": "platform@company.com"},
    {"team_name": "DevOps", "aws_account_id": "222222222222", "team_email": "devops@company.com"},
    ...
  ]'
```

---

## 🧪 Test the AI

```bash
# 1. Add a test team
curl -X POST "http://localhost:8001/api/teams" \
  -H "Content-Type: application/json" \
  -d '{"team_name":"Test Team","aws_account_id":"123456789012","team_email":"test@example.com"}'

# 2. Run AI analysis
curl "http://localhost:8001/api/ai/analyze/YOUR_TEAM_ID"

# 3. Get organization recommendations
curl "http://localhost:8001/api/ai/recommendations"
```

---

## 💰 Cost Comparison

| Component | Without AI | With AI |
|-----------|-----------|---------|
| S3 Storage | ~$0.03/mo | ~$0.03/mo |
| Gemini 3 Flash | $0 | ~$1-5/mo |
| Server (optional) | $6-15/mo | $6-15/mo |
| **Total** | **~$6-15/mo** | **~$7-20/mo** |

**Potential Savings from AI Recommendations:** $10,000+ / month 💸

---

## 🆘 Troubleshooting

### AI not working?
```bash
# Check if key is configured
curl http://localhost:8001/api/health
# Look for: "ai_configured": true
```

### No emails sent?
```bash
# Check SMTP config
docker-compose logs cost-agent | grep -i smtp
```

### View logs
```bash
docker-compose logs -f cost-agent
```

---

## 📄 Files in This Repo

```
aws-cost-agent/
├── docker-compose.yml    # 1-command deployment
├── .env.example          # Template for your keys
├── backend/
│   └── server.py         # Main AI agent code
└── README.md             # This file
```

---

## 🎯 Quick Start Summary

```bash
# 1. Clone/Download
git clone https://github.com/your-repo/aws-cost-agent
cd aws-cost-agent

# 2. Add your keys to .env
cp .env.example .env
nano .env  # Add your API keys

# 3. Start
docker-compose up -d

# 4. Add teams
curl -X POST "http://localhost:8001/api/teams/bulk" -d @teams.json

# 5. Test AI
curl "http://localhost:8001/api/ai/recommendations"

# Done! 🎉
```

---

**Built with ❤️ and 🤖 Gemini 3 Flash AI**
