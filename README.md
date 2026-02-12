# AWS Cost AI Agent 🤖

## AI-Powered AWS Cost Monitoring & Optimization

An intelligent automation agent that learns your AWS cost patterns, predicts future costs, detects anomalies, and provides optimization recommendations using **Gemini 3 Flash AI**.

---

## ⚡ Quick Installation

```bash
# Download and run installer
wget https://raw.githubusercontent.com/your-repo/aws-cost-agent/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

The installer will **securely prompt** you for:
- 🔑 Gemini API Key
- 🔑 AWS S3 Credentials  
- 🔑 Datadog API Keys
- 🔑 SMTP/Email Credentials

**All keys are stored securely with chmod 600 permissions.**

---

## 🎯 What It Does

| Feature | Description |
|---------|-------------|
| **🔍 Anomaly Detection** | AI explains WHY costs changed |
| **📈 Cost Prediction** | Predicts next month's costs |
| **💡 Optimization Tips** | AI recommendations to save money |
| **📊 Datadog Links** | Direct links to dashboards |
| **📧 Weekly Reports** | AI-powered email notifications |
| **🏢 84 Teams** | Each team sees only their costs |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS COST AI AGENT v3.0                               │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  GEMINI 3 FLASH │  │  COST ANALYZER  │  │   SCHEDULER     │             │
│  │  AI ENGINE      │  │                 │  │                 │             │
│  │                 │  │  • Compare MoM  │  │  • Weekly cron  │             │
│  │  • Why costs ↑  │  │  • Detect spike │  │  • Configurable │             │
│  │  • Optimize $   │  │  • Flag anomaly │  │  • Auto-run     │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           └────────────────────┴────────────────────┘                       │
│                                │                                            │
│  ┌─────────────────────────────┴─────────────────────────────────────────┐ │
│  │                        DATA & NOTIFICATIONS                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │ │
│  │  │  DATADOG    │  │  AWS S3     │  │  SMTP EMAIL │                   │ │
│  │  │  Cost Data  │  │  Storage    │  │  Reports    │                   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📧 Sample Team Report

```
╔══════════════════════════════════════════════════════════════════╗
║  🤖 AI-Powered Cost Report                                       ║
║  Platform Team - February 2026                                    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  💰 COST SUMMARY                                                  ║
║  ─────────────────────────────────────────────────               ║
║  Current Month:     $45,230.00                                   ║
║  Previous Month:    $38,500.00                                   ║
║  Change:            +17.5% ⚠️                                     ║
║                                                                   ║
║  🧠 AI ANALYSIS                                                   ║
║  ─────────────────────────────────────────────────               ║
║  Your costs increased 17.5% primarily due to:                    ║
║                                                                   ║
║  • EC2 scaling for product launch (+$4,200)                      ║
║    - 8 new m5.xlarge instances added Feb 5-7                     ║
║                                                                   ║
║  • RDS storage expansion (+$1,800)                               ║
║    - Database grew 40% due to new user signups                   ║
║                                                                   ║
║  💡 Recommendations:                                              ║
║  1. Convert 4 EC2 instances to Reserved (save $800/mo)           ║
║  2. Enable RDS storage auto-scaling threshold alerts             ║
║                                                                   ║
║  📈 PREDICTION: $48,000 - $52,000 next month                     ║
║                                                                   ║
║  🔗 DATADOG LINKS                                                 ║
║  • Cost Dashboard    • Cost Explorer    • Service Breakdown      ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 📧 Sample Admin Report

```
╔══════════════════════════════════════════════════════════════════╗
║  🤖 Organization Cost Summary - 84 Accounts                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  🧠 EXECUTIVE SUMMARY (AI-Generated)                             ║
║  ─────────────────────────────────────────────────               ║
║  Total AWS spend: $1,245,000 (+8.2% MoM)                         ║
║  12 accounts showed unusual cost patterns.                       ║
║  Key concern: DevOps team's 45% spike needs investigation.       ║
║                                                                   ║
║  ⚠️ TOP ANOMALIES                                                 ║
║  ─────────────────────────────────────────────────               ║
║  1. DevOps Team       $113,400    +45.2% ⚠️                       ║
║  2. Data Science      $89,200     +38.7% ⚠️                       ║
║  3. ML Platform       $67,800     +32.1% ⚠️                       ║
║                                                                   ║
║  💡 AI OPTIMIZATION RECOMMENDATIONS                               ║
║  ─────────────────────────────────────────────────               ║
║  1. Purchase 45 Reserved Instances (save $89K/year)              ║
║  2. Right-size 127 over-provisioned EC2s (save $34K/mo)          ║
║  3. Enable S3 Intelligent-Tiering (save $12K/mo)                 ║
║  4. Delete 45 unattached EBS volumes (save $4.5K/mo)             ║
║                                                                   ║
║  📊 Total Potential Savings: $69,500/month                       ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🔑 Required API Keys

| Key | Where to Get |
|-----|-------------|
| **GEMINI_API_KEY** | [Google AI Studio](https://aistudio.google.com/apikey) (free!) |
| **AWS Credentials** | AWS IAM Console |
| **DATADOG Keys** | Datadog → Org Settings → API Keys |
| **SMTP Credentials** | Your email provider |

---

## 🛠️ Commands

```bash
# Start agent
sudo systemctl start aws-cost-agent

# Stop agent
sudo systemctl stop aws-cost-agent

# View logs
sudo journalctl -u aws-cost-agent -f

# Check status
sudo systemctl status aws-cost-agent
```

---

## 📡 API Endpoints

```bash
# Health check
curl http://localhost:8001/api/health

# Add teams
curl -X POST "http://localhost:8001/api/teams/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"team_name":"Team1","aws_account_id":"123456789012","team_email":"team@company.com"}]'

# Get AI recommendations
curl http://localhost:8001/api/ai/recommendations

# Trigger weekly report
curl -X POST http://localhost:8001/api/trigger/weekly-report

# Preview admin report
curl http://localhost:8001/api/preview/admin-report
```

---

## 📁 Project Files

```
/opt/aws-cost-agent/
├── server.py          # Main agent code
├── .env               # API keys (secure, chmod 600)
├── venv/              # Python virtual environment
└── data/              # Local storage (if S3 not configured)
```

---

## 🔒 Security

- ✅ API keys entered securely (hidden input)
- ✅ `.env` file has chmod 600 (owner only)
- ✅ No hardcoded credentials in code
- ✅ `.gitignore` prevents committing secrets

---

## 💰 Cost

| Component | Monthly |
|-----------|---------|
| Gemini 3 Flash | ~$1-5 |
| AWS S3 | ~$0.03 |
| **Total** | **~$1-5** |

**Potential Savings**: $10,000+ /month from AI recommendations 💸

---

**Built with 🤖 Gemini 3 Flash AI**
