# AWS Cost Notification Agent - Documentation

## Overview

This is a **backend-only automation system** that:
1. Fetches AWS cost data from Datadog (or generates mock data for demo)
2. Compares current month vs last month costs
3. Detects cost anomalies (configurable threshold, default 20%)
4. Sends weekly email reports automatically
5. **Teams get only their data, Admins get all 84 accounts data**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AWS COST NOTIFICATION AGENT                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐ │
│  │  DATADOG SERVICE │───►│  COST ANALYZER   │───►│ EMAIL SERVICE  │ │
│  │  - Fetch metrics │    │  - Compare costs │    │ - SMTP/Outlook │ │
│  │  - aws.cost.*    │    │  - Detect anomaly│    │ - HTML reports │ │
│  └──────────────────┘    └──────────────────┘    └────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SCHEDULER (APScheduler)                    │   │
│  │         Weekly cron job → configurable day/time               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                       MONGODB STORAGE                         │   │
│  │  • teams - Team/Account mappings                              │   │
│  │  • cost_history - Historical cost data                        │   │
│  │  • anomalies - Detected anomalies                             │   │
│  │  • notification_config - Settings                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Team Registration
Each team is mapped to an AWS account:
```json
{
  "team_name": "Platform Team",
  "aws_account_id": "123456789012",
  "team_email": "platform-team@company.com",
  "admin_emails": ["team-lead@company.com"]
}
```

### 2. Cost Data Fetching
- Pulls cost data from Datadog API using `aws.cost.*` metrics
- Falls back to mock data if Datadog credentials not configured
- Groups by AWS service (EC2, RDS, S3, Lambda, etc.)

### 3. Anomaly Detection
- Compares current month cost vs previous month
- If percentage increase > threshold (default 20%) → Anomaly flagged
- Configurable threshold via API

### 4. Email Notifications
- **Team Report**: Individual team gets their account cost only
- **Admin Report**: Global admins get consolidated view of all 84 accounts
- HTML formatted emails with cost breakdown by service

### 5. Scheduling
- APScheduler runs weekly job
- Configurable day (Monday-Sunday) and hour (UTC)
- Can also be triggered manually via API

---

## API Endpoints

### Health & Status
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | Agent info |
| `/api/health` | GET | Health check |
| `/api/scheduler/status` | GET | Scheduler status & next run |

### Team Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teams` | GET | List all teams |
| `/api/teams` | POST | Add new team |
| `/api/teams/{id}` | GET | Get specific team |
| `/api/teams/{id}` | DELETE | Delete team |
| `/api/teams/bulk` | POST | Bulk create teams |

### Configuration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Get notification config |
| `/api/config` | PUT | Update config |

### Cost Data
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/costs/history` | GET | Get cost history |
| `/api/anomalies` | GET | Get detected anomalies |

### Manual Triggers
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trigger/weekly-report` | POST | Trigger full weekly report |
| `/api/trigger/team-report/{id}` | POST | Trigger single team report |
| `/api/preview/team-report/{id}` | GET | Preview team email |
| `/api/preview/admin-report` | GET | Preview admin email |

---

## Setup Instructions

### Step 1: Configure Environment Variables

Add to `/app/backend/.env`:
```bash
# Datadog Configuration (get from Datadog -> Organization Settings -> API Keys)
DATADOG_API_KEY=your_api_key_here
DATADOG_APP_KEY=your_app_key_here
DATADOG_SITE=datadoghq.com

# SMTP Configuration for Outlook
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
SENDER_EMAIL=aws-costs@company.com
```

### Step 2: Add Teams

**Option A: Single team via API**
```bash
curl -X POST "https://your-api-url/api/teams" \
  -H "Content-Type: application/json" \
  -d '{
    "team_name": "Platform Team",
    "aws_account_id": "123456789012",
    "team_email": "platform@company.com",
    "admin_emails": []
  }'
```

**Option B: Bulk upload from CSV/JSON**
```bash
# Example: Add multiple teams
curl -X POST "https://your-api-url/api/teams/bulk" \
  -H "Content-Type: application/json" \
  -d '[
    {"team_name": "Team A", "aws_account_id": "111111111111", "team_email": "teama@company.com"},
    {"team_name": "Team B", "aws_account_id": "222222222222", "team_email": "teamb@company.com"},
    {"team_name": "Team C", "aws_account_id": "333333333333", "team_email": "teamc@company.com"}
  ]'
```

### Step 3: Configure Settings

```bash
curl -X PUT "https://your-api-url/api/config" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_threshold": 25,
    "schedule_day": "monday",
    "schedule_hour": 9,
    "global_admin_emails": ["admin1@company.com", "admin2@company.com"]
  }'
```

### Step 4: Test

**Preview a team report:**
```bash
curl "https://your-api-url/api/preview/team-report/{team_id}"
```

**Preview admin report:**
```bash
curl "https://your-api-url/api/preview/admin-report"
```

**Trigger manual report:**
```bash
curl -X POST "https://your-api-url/api/trigger/weekly-report"
```

---

## Code Structure Explained

### 1. `DatadogService` Class
```python
class DatadogService:
    """Fetches AWS cost data from Datadog API"""
    
    async def get_cost_metrics(account_id, start_date, end_date):
        # Calls Datadog API: GET /api/v1/query
        # Query: avg:aws.cost.amortized{account_id:xxx}
        # Returns: total_cost, service_breakdown
```

### 2. `CostAnalyzer` Class
```python
class CostAnalyzer:
    """Compares costs and detects anomalies"""
    
    async def analyze_team_costs(team, threshold):
        # 1. Fetch current month cost
        # 2. Fetch previous month cost
        # 3. Calculate percentage change
        # 4. Flag as anomaly if change > threshold
```

### 3. `EmailService` Class
```python
class EmailService:
    """Sends HTML formatted email reports"""
    
    async def send_team_report(team, cost_data, anomalies, config):
        # Generates team-specific HTML email
        # Sends via SMTP to team_email only
    
    async def send_admin_report(all_teams_data, all_anomalies, config):
        # Generates consolidated HTML email
        # Sends to all global_admin_emails
```

### 4. Scheduler (APScheduler)
```python
# Configured via NotificationConfig
scheduler.add_job(
    run_weekly_report,
    CronTrigger(day_of_week='monday', hour=9, minute=0),
    id='weekly_cost_report'
)
```

### 5. Main Job: `run_weekly_report()`
```python
async def run_weekly_report():
    # 1. Load all teams from MongoDB
    # 2. For each team:
    #    - Fetch cost data from Datadog
    #    - Analyze costs (current vs previous)
    #    - Send individual team email
    #    - Store cost record in DB
    #    - If anomaly detected → store in anomalies collection
    # 3. Send admin consolidated report
```

---

## Data Models

### Team
| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| team_name | string | Display name |
| aws_account_id | string | 12-digit AWS account ID |
| team_email | email | Team notification email |
| admin_emails | list | Optional team admins |

### Cost Data
| Field | Type | Description |
|-------|------|-------------|
| aws_account_id | string | AWS account |
| month | string | YYYY-MM format |
| total_cost | float | Total cost in USD |
| service_breakdown | dict | Cost per AWS service |

### Cost Anomaly
| Field | Type | Description |
|-------|------|-------------|
| aws_account_id | string | AWS account |
| team_name | string | Team name |
| current_cost | float | Current month cost |
| previous_cost | float | Previous month cost |
| percentage_change | float | % change |
| is_anomaly | bool | Exceeds threshold? |

### Notification Config
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| anomaly_threshold | float | 20.0 | % increase to flag |
| schedule_day | string | "monday" | Weekly run day |
| schedule_hour | int | 9 | Hour in UTC |
| global_admin_emails | list | [] | Admin email list |

---

## Security Considerations

1. **API Keys**: Store Datadog API/App keys in environment variables, never in code
2. **SMTP Credentials**: Use app passwords or OAuth for Outlook
3. **Access Control**: Currently no auth - add JWT if exposing to internet
4. **Data Isolation**: Teams only see their own data via email reports

---

## To Make It Production-Ready

1. **Add Datadog credentials** to `.env`
2. **Configure SMTP** for Outlook/Office 365
3. **Import all 84 teams** via bulk API
4. **Set admin emails** in config
5. **Test** with preview endpoints first
6. **Enable scheduler** - it auto-starts on backend startup

---

## Datadog Setup (If Not Already Done)

1. Go to Datadog → Organization Settings → API Keys
2. Create new API Key (for read access)
3. Create new Application Key (for advanced API features)
4. Ensure AWS Cost Management integration is enabled in Datadog
5. Verify `aws.cost.*` metrics are being collected

---

## Troubleshooting

**Q: No data coming from Datadog?**
- Check API/App keys are correct
- Verify Datadog site (datadoghq.com vs datadoghq.eu)
- Check AWS Cost Management integration in Datadog is active

**Q: Emails not sending?**
- Verify SMTP credentials
- Check firewall allows outbound port 587
- Try with Gmail first (smtp.gmail.com, port 587)

**Q: Scheduler not running?**
- Check `/api/scheduler/status` endpoint
- Verify backend is running continuously
- Check logs: `tail -f /var/log/supervisor/backend.*.log`

---

## Example API Calls

```bash
# Base URL
API_URL="https://cost-anomaly-report.preview.emergentagent.com"

# Add a team
curl -X POST "$API_URL/api/teams" \
  -H "Content-Type: application/json" \
  -d '{"team_name":"DevOps","aws_account_id":"123456789012","team_email":"devops@company.com"}'

# Get all teams
curl "$API_URL/api/teams"

# Update config
curl -X PUT "$API_URL/api/config" \
  -H "Content-Type: application/json" \
  -d '{"anomaly_threshold":30,"schedule_day":"friday","schedule_hour":10}'

# Preview admin report
curl "$API_URL/api/preview/admin-report"

# Trigger weekly report manually
curl -X POST "$API_URL/api/trigger/weekly-report"

# Check scheduler status
curl "$API_URL/api/scheduler/status"
```
