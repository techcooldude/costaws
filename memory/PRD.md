# AWS Cost AI Agent - PRD

## Original Problem Statement
Create an intelligent AWS cost notification system for 84 accounts managed by AWS Organization that:
- Automatically learns cost patterns using AI (Gemini 3 Flash)
- Explains WHY costs changed
- Predicts future costs based on trends
- Provides optimization recommendations
- Sends weekly email reports with AI insights
- Includes Datadog dashboard links
- Each team gets their own cost data, admins get all teams' data
- Uses AWS S3 for storage (no database)

## Architecture
- **Backend**: FastAPI with APScheduler
- **Storage**: AWS S3 (with local file fallback)
- **AI**: Gemini 3 Flash for intelligent analysis
- **Data Source**: Datadog API (with mock fallback)
- **Notifications**: SMTP Email (Outlook compatible)

## AI Features
1. **Anomaly Explanation**: AI explains why costs changed
2. **Cost Prediction**: Predicts next month costs from trends
3. **Optimization Recommendations**: Org-wide savings opportunities
4. **Executive Summary**: AI-generated summaries for admins
5. **Pattern Learning**: Stores insights for continuous learning

## User Personas
1. **Team Members**: Receive AI-powered cost reports with explanations
2. **Admins**: Receive consolidated report with AI recommendations

## What's Been Implemented (Feb 12, 2026)
1. **CostAIService**: Gemini 3 Flash integration for:
   - Anomaly analysis
   - Cost predictions
   - Optimization recommendations
   - Executive summaries
2. **S3Storage**: JSON storage with AI insights collection
3. **DatadogService**: Cost data fetching with DD links
4. **EmailService**: AI-enhanced HTML email reports
5. **REST APIs**: Full CRUD + AI endpoints

## S3 Bucket Structure
```
aws-cost-agent-data/
├── config/notification_config.json
├── teams/teams.json
├── costs/{year}/{month}/{account_id}.json
├── anomalies/{year}/{month}/anomalies.json
└── ai_insights/{year}/{month}/insights.json  ← NEW: AI learning
```

## API Endpoints
- `POST /api/ai/analyze/{team_id}` - AI analysis for team
- `GET /api/ai/recommendations` - Org-wide AI recommendations
- `GET /api/ai/insights` - Historical AI insights

## Next Steps
1. Add Gemini API key (GEMINI_API_KEY)
2. Configure AWS S3 credentials
3. Configure Datadog credentials
4. Configure SMTP for Outlook
5. Import all 84 teams
6. Test with real data
