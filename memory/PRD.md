# AWS Cost Notification Agent - PRD

## Original Problem Statement
Create a one-page notification system for AWS costs across 84 accounts managed by AWS Organization. The system should:
- Show last month cost and compare with current month expenses
- Pull data from Datadog where all AWS costs are available
- Send automatic weekly notifications with summary and detailed cost anomalies
- Each team gets their own cost data, admins get all teams' data
- Backend-only automation (no web dashboard)
- Use AWS S3 for storage (no database)

## Architecture
- **Backend**: FastAPI with APScheduler
- **Storage**: AWS S3 (with local file fallback for demo)
- **Data Source**: Datadog API (with mock fallback)
- **Notifications**: SMTP Email (Outlook compatible)

## User Personas
1. **Team Members**: Receive weekly cost reports for their specific AWS account only
2. **Admins**: Receive consolidated report for all 84 accounts with anomaly highlights

## Core Requirements (Static)
- [x] Fetch AWS cost data from Datadog
- [x] Compare current vs previous month costs
- [x] Detect anomalies (configurable threshold)
- [x] Send team-specific emails
- [x] Send admin consolidated emails
- [x] Weekly automated scheduling
- [x] Team management API
- [x] Configuration management API
- [x] S3 storage (with local fallback)

## What's Been Implemented (Feb 12, 2026)
1. **S3Storage**: JSON file storage in S3 (local fallback when no credentials)
2. **DatadogService**: Fetches aws.cost.* metrics (mock data fallback)
3. **CostAnalyzer**: Compares months, calculates % change, flags anomalies
4. **EmailService**: Generates HTML emails, sends via SMTP
5. **APScheduler**: Weekly cron job, configurable day/hour
6. **REST APIs**: Full CRUD for teams, config, history

## S3 Bucket Structure
```
aws-cost-agent-data/
├── config/notification_config.json
├── teams/teams.json
├── costs/{year}/{month}/{account_id}.json
└── anomalies/{year}/{month}/anomalies.json
```

## Prioritized Backlog

### P0 - Done
- [x] S3 storage implementation
- [x] Local file fallback for demo
- [x] Core cost fetching logic
- [x] Anomaly detection
- [x] Email templates (team & admin)
- [x] Team management APIs
- [x] Scheduler setup

### P1 - Next
- [ ] Configure AWS S3 credentials
- [ ] Configure Datadog API credentials
- [ ] Configure SMTP credentials for Outlook
- [ ] Bulk import 84 teams

### P2 - Future
- [ ] Lambda deployment option
- [ ] Historical trend analysis
- [ ] Service-level anomaly detection
- [ ] Slack notification option

## Next Tasks
1. Create S3 bucket and IAM credentials
2. Add AWS credentials to .env
3. Add Datadog credentials to .env
4. Configure SMTP for Outlook
5. Import all 84 teams
6. Test with real data
