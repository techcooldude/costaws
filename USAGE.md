# AWS Cost AI Agent - Usage Guide

## 📖 Table of Contents

1. [Quick Start](#quick-start)
2. [Manual Report Triggers](#manual-report-triggers)
3. [Team Management](#team-management)
4. [Configuration](#configuration)
5. [AI Analysis](#ai-analysis)
6. [Monitoring & Logs](#monitoring--logs)
7. [EC2 Security Setup](#ec2-security-setup)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Check Agent Status
```bash
# Is the agent running?
curl http://localhost:8001/api/health

# Expected response:
{
  "status": "healthy",
  "storage": "S3",
  "ai_configured": true
}
```

### Check Scheduler
```bash
curl http://localhost:8001/api/scheduler/status

# Shows next scheduled run time
```

---

## 📧 Manual Report Triggers

### 1. Trigger Full Weekly Report (All 84 Teams + Admin)

```bash
curl -X POST http://localhost:8001/api/trigger/weekly-report
```

**What happens:**
- Fetches cost data for all 84 teams from Datadog
- Runs AI analysis on each team
- Sends individual email to each team (their data only)
- Sends consolidated report to all admin emails

---

### 2. Trigger Report for Single Team

```bash
# First, get team ID
curl http://localhost:8001/api/teams

# Then trigger for specific team
curl -X POST http://localhost:8001/api/trigger/team-report/{team_id}
```

**Example:**
```bash
curl -X POST http://localhost:8001/api/trigger/team-report/abc123-def456-789
```

---

### 3. Preview Reports (Without Sending Email)

**Preview Team Report:**
```bash
curl http://localhost:8001/api/preview/team-report/{team_id}
```

**Preview Admin Report:**
```bash
curl http://localhost:8001/api/preview/admin-report
```

**Why use preview?**
- Test before sending
- Check AI analysis quality
- Verify data is correct
- See HTML email content

---

### 4. Quick Reference Table

| Action | Command |
|--------|---------|
| **Full report (all teams)** | `curl -X POST http://localhost:8001/api/trigger/weekly-report` |
| **Single team report** | `curl -X POST http://localhost:8001/api/trigger/team-report/{id}` |
| **Preview team** | `curl http://localhost:8001/api/preview/team-report/{id}` |
| **Preview admin** | `curl http://localhost:8001/api/preview/admin-report` |

---

## 👥 Team Management

### List All Teams
```bash
curl http://localhost:8001/api/teams
```

### Add Single Team
```bash
curl -X POST http://localhost:8001/api/teams \
  -H "Content-Type: application/json" \
  -d '{
    "team_name": "Platform Team",
    "aws_account_id": "123456789012",
    "team_email": "platform@company.com",
    "admin_emails": ["lead@company.com"]
  }'
```

### Add Multiple Teams (Bulk)
```bash
curl -X POST http://localhost:8001/api/teams/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"team_name": "Team A", "aws_account_id": "111111111111", "team_email": "teama@company.com"},
    {"team_name": "Team B", "aws_account_id": "222222222222", "team_email": "teamb@company.com"},
    {"team_name": "Team C", "aws_account_id": "333333333333", "team_email": "teamc@company.com"}
  ]'
```

### Add Teams from JSON File
```bash
# Create teams.json file first
curl -X POST http://localhost:8001/api/teams/bulk \
  -H "Content-Type: application/json" \
  -d @teams.json
```

### Get Specific Team
```bash
curl http://localhost:8001/api/teams/{team_id}
```

### Delete Team
```bash
curl -X DELETE http://localhost:8001/api/teams/{team_id}
```

---

## ⚙️ Configuration

### View Current Configuration
```bash
curl http://localhost:8001/api/config
```

### Update Configuration
```bash
curl -X PUT http://localhost:8001/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_threshold": 25,
    "schedule_day": "friday",
    "schedule_hour": 10,
    "global_admin_emails": ["admin1@company.com", "admin2@company.com"],
    "ai_enabled": true
  }'
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `anomaly_threshold` | float | 20.0 | % increase to flag as anomaly |
| `schedule_day` | string | "monday" | Day for weekly report |
| `schedule_hour` | int | 9 | Hour in UTC (0-23) |
| `global_admin_emails` | list | [] | Emails for admin report |
| `ai_enabled` | bool | true | Enable/disable AI analysis |

---

## 🤖 AI Analysis

### Run AI Analysis for Single Team
```bash
curl -X POST http://localhost:8001/api/ai/analyze/{team_id}
```

**Response includes:**
- Cost comparison (current vs previous month)
- AI explanation of why costs changed
- Next month prediction
- Datadog dashboard links

### Get Organization-Wide AI Recommendations
```bash
curl http://localhost:8001/api/ai/recommendations
```

**Response includes:**
- Top savings opportunities across all teams
- Reserved Instance recommendations
- Right-sizing suggestions
- Cleanup recommendations

### View Historical AI Insights
```bash
curl http://localhost:8001/api/ai/insights
```

---

## 📊 Cost Data

### View Cost History
```bash
# All history
curl http://localhost:8001/api/costs/history

# Filter by team
curl "http://localhost:8001/api/costs/history?team_name=Platform%20Team"

# Filter by month
curl "http://localhost:8001/api/costs/history?month=2026-02"

# Limit results
curl "http://localhost:8001/api/costs/history?limit=10"
```

### View Detected Anomalies
```bash
# All anomalies
curl http://localhost:8001/api/anomalies

# Filter by team
curl "http://localhost:8001/api/anomalies?team_name=DevOps%20Team"
```

---

## 📋 Monitoring & Logs

### Systemd Commands
```bash
# Start agent
sudo systemctl start aws-cost-agent

# Stop agent
sudo systemctl stop aws-cost-agent

# Restart agent
sudo systemctl restart aws-cost-agent

# Check status
sudo systemctl status aws-cost-agent

# Enable auto-start on boot
sudo systemctl enable aws-cost-agent
```

### View Logs
```bash
# Live logs (follow mode)
sudo journalctl -u aws-cost-agent -f

# Last 100 lines
sudo journalctl -u aws-cost-agent -n 100

# Logs from today
sudo journalctl -u aws-cost-agent --since today

# Logs from last hour
sudo journalctl -u aws-cost-agent --since "1 hour ago"

# Search for errors
sudo journalctl -u aws-cost-agent | grep -i error
```

---

## 🔒 EC2 Security Setup

### Security Group - Inbound Rules

| Type | Port | Source | Description |
|------|------|--------|-------------|
| SSH | 22 | Your IP only (`x.x.x.x/32`) | Admin access |
| Custom TCP | 8001 | Your IP only (optional) | API access |

**Note:** Port 8001 is optional. If you only use scheduled reports, don't open it.

### Security Group - Outbound Rules

| Type | Port | Destination | Description |
|------|------|-------------|-------------|
| HTTPS | 443 | `0.0.0.0/0` | Datadog API, Gemini API, S3 |
| SMTP | 587 | `0.0.0.0/0` | Send emails (Outlook) |

### AWS CLI Commands
```bash
# Allow SSH from your IP
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxx \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32

# Allow HTTPS outbound
aws ec2 authorize-security-group-egress \
  --group-id sg-xxxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow SMTP outbound
aws ec2 authorize-security-group-egress \
  --group-id sg-xxxxxx \
  --protocol tcp \
  --port 587 \
  --cidr 0.0.0.0/0
```

### Security Best Practices

| ✅ Do | ❌ Don't |
|-------|---------|
| Restrict SSH to your IP only | Open SSH to 0.0.0.0/0 |
| Use security groups | Rely on OS firewall only |
| Keep port 8001 closed if not needed | Expose API to internet |
| Use IAM roles on EC2 | Hardcode AWS credentials |
| Rotate API keys regularly | Share API keys |

---

## 🔧 Troubleshooting

### Agent Not Starting
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

### Emails Not Sending
```bash
# Check SMTP config in logs
sudo journalctl -u aws-cost-agent | grep -i smtp

# Verify .env has correct SMTP settings
cat /opt/aws-cost-agent/.env | grep SMTP

# Test connectivity to SMTP server
nc -zv smtp.office365.com 587
```

### AI Analysis Not Working
```bash
# Check if Gemini key is configured
curl http://localhost:8001/api/health

# Look for "ai_configured": true

# Check logs for AI errors
sudo journalctl -u aws-cost-agent | grep -i gemini
```

### No Data from Datadog
```bash
# Check Datadog config
curl http://localhost:8001/api/storage/info

# Verify Datadog keys in .env
cat /opt/aws-cost-agent/.env | grep DATADOG

# Check logs for Datadog errors
sudo journalctl -u aws-cost-agent | grep -i datadog
```

### S3 Storage Issues
```bash
# Check S3 config
curl http://localhost:8001/api/storage/info

# If using local fallback, data stored in:
ls -la /opt/aws-cost-agent/data/

# Check AWS credentials
cat /opt/aws-cost-agent/.env | grep AWS
```

---

## 📝 Example Workflows

### First Time Setup
```bash
# 1. Check agent is running
curl http://localhost:8001/api/health

# 2. Add your teams
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

# 6. Check logs
sudo journalctl -u aws-cost-agent -f
```

### Daily Operations
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

### Debug a Team's Costs
```bash
# Get team ID
curl http://localhost:8001/api/teams | grep -A5 "DevOps"

# Run AI analysis
curl -X POST http://localhost:8001/api/ai/analyze/{team_id}

# View cost history
curl "http://localhost:8001/api/costs/history?team_name=DevOps%20Team"
```

---

## 📞 API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/teams` | GET | List all teams |
| `/api/teams` | POST | Add team |
| `/api/teams/bulk` | POST | Add multiple teams |
| `/api/teams/{id}` | DELETE | Delete team |
| `/api/config` | GET | Get config |
| `/api/config` | PUT | Update config |
| `/api/trigger/weekly-report` | POST | Trigger full report |
| `/api/trigger/team-report/{id}` | POST | Trigger team report |
| `/api/preview/team-report/{id}` | GET | Preview team report |
| `/api/preview/admin-report` | GET | Preview admin report |
| `/api/ai/analyze/{id}` | POST | AI analysis for team |
| `/api/ai/recommendations` | GET | Org-wide AI tips |
| `/api/costs/history` | GET | Cost history |
| `/api/anomalies` | GET | Detected anomalies |
| `/api/scheduler/status` | GET | Scheduler info |

---

**Need help?** Check logs: `sudo journalctl -u aws-cost-agent -f`
