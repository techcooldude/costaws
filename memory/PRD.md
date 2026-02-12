# AWS Cost Notification Agent - PRD

## Original Problem Statement
Create a one-page notification system for AWS costs across 84 accounts managed by AWS Organization. The system should:
- Show last month cost and compare with current month expenses
- Pull data from Datadog where all AWS costs are available
- Send automatic weekly notifications with summary and detailed cost anomalies
- Each team gets their own cost data, admins get all teams' data
- Backend-only automation (no web dashboard)

## Architecture
- **Backend**: FastAPI with APScheduler
- **Database**: MongoDB
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

## What's Been Implemented (Feb 12, 2026)
1. **DatadogService**: Fetches aws.cost.* metrics (mock data fallback when no credentials)
2. **CostAnalyzer**: Compares months, calculates % change, flags anomalies
3. **EmailService**: Generates HTML emails, sends via SMTP
4. **APScheduler**: Weekly cron job, configurable day/hour
5. **REST APIs**:
   - Team CRUD + bulk create
   - Configuration management
   - Cost history & anomalies queries
   - Manual triggers & previews

## Prioritized Backlog

### P0 - Done
- [x] Core cost fetching logic
- [x] Anomaly detection
- [x] Email templates (team & admin)
- [x] Team management APIs
- [x] Scheduler setup

### P1 - Next
- [ ] Datadog API integration (need credentials)
- [ ] SMTP configuration (need Outlook credentials)
- [ ] Bulk import 84 teams from CSV

### P2 - Future
- [ ] JWT authentication for API security
- [ ] Historical trend analysis
- [ ] Service-level anomaly detection
- [ ] Slack notification option
- [ ] Daily digest option

## Next Tasks
1. Configure Datadog credentials (DATADOG_API_KEY, DATADOG_APP_KEY)
2. Configure SMTP credentials for Outlook
3. Import all 84 teams (use /api/teams/bulk endpoint)
4. Set global admin emails
5. Test with real data
