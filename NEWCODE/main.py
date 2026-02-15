"""
AWS Cost AI Agent - Main Application
Internal Network Only (127.0.0.1) with Vertex AI
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings
from app.services.vertex_ai_service import VertexAIService
from app.services.storage_service import S3Storage
from app.services.datadog_service import DatadogService
from app.api.routes import router as api_router
from app.api.middleware import IPWhitelistMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware

# Logging setup
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
scheduler = AsyncIOScheduler()
ai_service: VertexAIService = None
storage: S3Storage = None
datadog: DatadogService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global ai_service, storage, datadog
    
    logger.info("=" * 70)
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Binding to: {settings.HOST}:{settings.PORT} (INTERNAL ONLY)")
    logger.info("=" * 70)
    
    # Initialize services
    ai_service = VertexAIService()
    storage = S3Storage()
    datadog = DatadogService()
    
    # Store in app state
    app.state.ai_service = ai_service
    app.state.storage = storage
    app.state.datadog = datadog
    
    # Start scheduler
    schedule_weekly_analysis()
    scheduler.start()
    logger.info("✓ Scheduler started")
    
    logger.info("✓ Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    scheduler.shutdown()
    logger.info("✓ Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered AWS cost monitoring (Internal Network Only)",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(IPWhitelistMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "message": "Internal network only - Vertex AI powered"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health = {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "storage": "healthy" if storage and (storage.use_s3 or storage.local_storage_dir.exists()) else "degraded",
            "vertex_ai": "healthy" if ai_service and ai_service.initialized else "not_configured",
            "datadog": "configured" if datadog and datadog.api_key else "not_configured",
            "scheduler": "running" if scheduler.running else "stopped"
        }
    }
    
    # Overall health
    if health["services"]["storage"] == "degraded":
        health["status"] = "degraded"
    
    return health


# ============================================================================
# COST ANALYSIS & EMAIL FUNCTIONS
# ============================================================================

async def analyze_and_notify():
    """Main scheduled job - analyze costs and send notifications"""
    logger.info("=" * 70)
    logger.info("Starting scheduled cost analysis...")
    logger.info("=" * 70)
    
    try:
        teams = storage.get_all_teams()
        if not teams:
            logger.warning("No teams configured")
            return
        
        logger.info(f"Analyzing costs for {len(teams)} teams")
        
        all_team_data = []
        all_anomalies = []
        
        # Analyze each team
        for team in teams:
            try:
                team_data = await analyze_team_costs(team)
                if team_data:
                    all_team_data.append(team_data)
                    
                    # Check for anomaly
                    if team_data.get('is_anomaly'):
                        all_anomalies.append(team_data)
                        logger.warning(f"⚠️  Anomaly detected: {team['team_name']} - {team_data['percentage_change']:.1f}% change")
                        
                        # Send individual team alert
                        await send_anomaly_alert(team, team_data)
                        
                        # Save anomaly
                        storage.save_anomaly({
                            "aws_account_id": team["aws_account_id"],
                            "team_name": team["team_name"],
                            "current_month": team_data["current_month"],
                            "current_cost": team_data["current_month_cost"],
                            "previous_month": team_data["previous_month"],
                            "previous_cost": team_data["previous_month_cost"],
                            "percentage_change": team_data["percentage_change"],
                            "is_anomaly": True,
                            "ai_explanation": team_data.get("ai_analysis", {}).get("ai_analysis"),
                            "detected_at": datetime.now(timezone.utc).isoformat()
                        })
                
            except Exception as e:
                logger.error(f"Error analyzing {team.get('team_name', 'unknown')}: {e}")
                continue
        
        # Send executive summary
        if all_team_data:
            await send_executive_summary(all_team_data, all_anomalies)
        
        logger.info("=" * 70)
        logger.info(f"✓ Analysis complete: {len(all_team_data)} teams, {len(all_anomalies)} anomalies")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error in scheduled analysis: {e}", exc_info=True)


async def analyze_team_costs(team: Dict) -> Dict:
    """Analyze costs for a single team"""
    try:
        # Get current and previous month dates
        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Format dates
        current_month_str = current_month_start.strftime("%Y-%m-%d")
        current_month_end_str = now.strftime("%Y-%m-%d")
        previous_month_str = previous_month_start.strftime("%Y-%m-%d")
        previous_month_end_str = previous_month_end.strftime("%Y-%m-%d")
        
        # Fetch current month costs
        current_data = await datadog.get_cost_metrics(
            team["aws_account_id"],
            current_month_str,
            current_month_end_str
        )
        
        # Fetch previous month costs
        previous_data = await datadog.get_cost_metrics(
            team["aws_account_id"],
            previous_month_str,
            previous_month_end_str
        )
        
        current_cost = current_data.get("total_cost", 0)
        previous_cost = previous_data.get("total_cost", 0)
        
        # Calculate change
        percentage_change = 0
        if previous_cost > 0:
            percentage_change = ((current_cost - previous_cost) / previous_cost) * 100
        
        # Save cost record
        storage.save_cost_record({
            "aws_account_id": team["aws_account_id"],
            "team_name": team["team_name"],
            "month": current_month_start.strftime("%Y-%m"),
            "total_cost": current_cost,
            "service_breakdown": current_data.get("service_breakdown", {}),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Check if anomaly
        config = storage.get_config()
        threshold = config.get("anomaly_threshold", settings.ANOMALY_THRESHOLD)
        is_anomaly = abs(percentage_change) > threshold
        
        team_data = {
            "team_name": team["team_name"],
            "aws_account_id": team["aws_account_id"],
            "team_email": team.get("team_email"),
            "current_month": current_month_start.strftime("%Y-%m"),
            "current_month_cost": current_cost,
            "previous_month": previous_month_start.strftime("%Y-%m"),
            "previous_month_cost": previous_cost,
            "percentage_change": percentage_change,
            "is_anomaly": is_anomaly,
            "service_breakdown": current_data.get("service_breakdown", {}),
            "previous_service_breakdown": previous_data.get("service_breakdown", {})
        }
        
        # Get AI analysis for anomalies
        if is_anomaly and ai_service and ai_service.initialized:
            ai_analysis = await ai_service.analyze_cost_anomaly(team_data)
            team_data["ai_analysis"] = ai_analysis
        
        return team_data
        
    except Exception as e:
        logger.error(f"Error analyzing team {team.get('team_name')}: {e}")
        return None


async def send_anomaly_alert(team: Dict, team_data: Dict):
    """Send email alert for cost anomaly"""
    try:
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email")
            return
        
        recipients = [team.get("team_email")]
        if team.get("admin_emails"):
            recipients.extend(team["admin_emails"])
        
        subject = f"🚨 AWS Cost Anomaly Detected - {team['team_name']}"
        
        # Build email body
        body = f"""
<h2>AWS Cost Anomaly Alert</h2>

<p><strong>Team:</strong> {team['team_name']}</p>
<p><strong>AWS Account:</strong> {team['aws_account_id']}</p>

<h3>Cost Summary</h3>
<table border="1" cellpadding="5" cellspacing="0">
    <tr>
        <td><strong>Current Month ({team_data['current_month']})</strong></td>
        <td>${team_data['current_month_cost']:,.2f}</td>
    </tr>
    <tr>
        <td><strong>Previous Month ({team_data['previous_month']})</strong></td>
        <td>${team_data['previous_month_cost']:,.2f}</td>
    </tr>
    <tr style="background-color: {'#ffcccc' if team_data['percentage_change'] > 0 else '#ccffcc'}">
        <td><strong>Change</strong></td>
        <td>{team_data['percentage_change']:+.1f}%</td>
    </tr>
</table>

<h3>Service Breakdown</h3>
<table border="1" cellpadding="5" cellspacing="0">
    <tr>
        <th>Service</th>
        <th>Current Cost</th>
    </tr>
"""
        
        for service, cost in sorted(team_data['service_breakdown'].items(), key=lambda x: x[1], reverse=True):
            body += f"    <tr><td>{service}</td><td>${cost:,.2f}</td></tr>\n"
        
        body += "</table>\n"
        
        # Add AI analysis
        if team_data.get("ai_analysis", {}).get("ai_analysis"):
            body += f"""
<h3>🤖 AI Analysis</h3>
<div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">
    <pre style="white-space: pre-wrap;">{team_data['ai_analysis']['ai_analysis']}</pre>
</div>
"""
        
        body += f"""
<hr>
<p style="color: #666; font-size: 12px;">
Generated by {settings.APP_NAME} v{settings.VERSION} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
</p>
"""
        
        await send_email(recipients, subject, body)
        logger.info(f"✓ Anomaly alert sent to {team['team_name']}")
        
    except Exception as e:
        logger.error(f"Error sending anomaly alert: {e}")


async def send_executive_summary(all_team_data: List[Dict], all_anomalies: List[Dict]):
    """Send executive summary to admins"""
    try:
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email")
            return
        
        config = storage.get_config()
        admin_emails = config.get("global_admin_emails", settings.get_admin_emails())
        
        if not admin_emails:
            logger.warning("No admin emails configured")
            return
        
        total_current = sum(t['current_month_cost'] for t in all_team_data)
        total_previous = sum(t['previous_month_cost'] for t in all_team_data)
        total_change = ((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0
        
        subject = f"AWS Cost Weekly Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        
        # Get AI executive summary
        ai_summary = ""
        if ai_service and ai_service.initialized:
            ai_summary = await ai_service.generate_executive_summary(all_team_data, all_anomalies)
        
        body = f"""
<h2>AWS Cost Executive Summary</h2>

<h3>🤖 AI Summary</h3>
<div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin-bottom: 20px;">
    <p style="margin: 0; line-height: 1.6;">{ai_summary if ai_summary else "AI analysis not available"}</p>
</div>

<h3>Overview</h3>
<table border="1" cellpadding="5" cellspacing="0">
    <tr>
        <td><strong>Total AWS Accounts</strong></td>
        <td>{len(all_team_data)}</td>
    </tr>
    <tr>
        <td><strong>Current Month Spend</strong></td>
        <td>${total_current:,.2f}</td>
    </tr>
    <tr>
        <td><strong>Previous Month Spend</strong></td>
        <td>${total_previous:,.2f}</td>
    </tr>
    <tr style="background-color: {'#ffcccc' if total_change > 0 else '#ccffcc'}">
        <td><strong>Month-over-Month Change</strong></td>
        <td>{total_change:+.1f}%</td>
    </tr>
    <tr>
        <td><strong>Anomalies Detected</strong></td>
        <td>{len(all_anomalies)}</td>
    </tr>
</table>

<h3>Top 10 Spending Teams</h3>
<table border="1" cellpadding="5" cellspacing="0" style="width: 100%;">
    <tr>
        <th>Team</th>
        <th>Current Cost</th>
        <th>Previous Cost</th>
        <th>Change %</th>
    </tr>
"""
        
        top_teams = sorted(all_team_data, key=lambda x: x['current_month_cost'], reverse=True)[:10]
        for team in top_teams:
            bg_color = '#ffcccc' if team['percentage_change'] > 20 else ('#ccffcc' if team['percentage_change'] < -10 else '#ffffff')
            body += f"""    <tr style="background-color: {bg_color}">
        <td>{team['team_name']}</td>
        <td>${team['current_month_cost']:,.2f}</td>
        <td>${team['previous_month_cost']:,.2f}</td>
        <td>{team['percentage_change']:+.1f}%</td>
    </tr>\n"""
        
        body += "</table>\n"
        
        # Anomalies section
        if all_anomalies:
            body += f"""
<h3>⚠️ Cost Anomalies ({len(all_anomalies)} detected)</h3>
<table border="1" cellpadding="5" cellspacing="0" style="width: 100%;">
    <tr>
        <th>Team</th>
        <th>Current Cost</th>
        <th>Change %</th>
    </tr>
"""
            
            for anomaly in sorted(all_anomalies, key=lambda x: abs(x['percentage_change']), reverse=True)[:5]:
                body += f"""    <tr style="background-color: #ffcccc;">
        <td>{anomaly['team_name']}</td>
        <td>${anomaly['current_month_cost']:,.2f}</td>
        <td style="font-weight: bold;">{anomaly['percentage_change']:+.1f}%</td>
    </tr>\n"""
            
            body += "</table>\n"
        
        body += f"""
<hr>
<p style="color: #666; font-size: 12px;">
Generated by {settings.APP_NAME} v{settings.VERSION} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
</p>
"""
        
        await send_email(admin_emails, subject, body)
        logger.info(f"✓ Executive summary sent to {len(admin_emails)} admins")
        
    except Exception as e:
        logger.error(f"Error sending executive summary: {e}")


async def send_email(recipients: List[str], subject: str, html_body: str):
    """Send email via SMTP"""
    try:
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = settings.SENDER_EMAIL
        message['To'] = ', '.join(recipients)
        
        html_part = MIMEText(html_body, 'html')
        message.attach(html_part)
        
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True
        )
        
        logger.info(f"Email sent to {len(recipients)} recipients")
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


def schedule_weekly_analysis():
    """Schedule the weekly cost analysis job"""
    config = storage.get_config() if storage else {}
    
    day = config.get('schedule_day', settings.SCHEDULE_DAY).lower()
    hour = config.get('schedule_hour', settings.SCHEDULE_HOUR)
    
    day_map = {
        'monday': 'mon', 'tuesday': 'tue', 'wednesday': 'wed',
        'thursday': 'thu', 'friday': 'fri', 'saturday': 'sat', 'sunday': 'sun'
    }
    
    cron_day = day_map.get(day, 'mon')
    
    trigger = CronTrigger(
        day_of_week=cron_day,
        hour=hour,
        minute=0,
        timezone='UTC'
    )
    
    scheduler.add_job(
        analyze_and_notify,
        trigger=trigger,
        id='weekly_analysis',
        replace_existing=True,
        name='Weekly Cost Analysis'
    )
    
    logger.info(f"✓ Scheduled weekly analysis: Every {day} at {hour}:00 UTC")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
