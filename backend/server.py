"""
AWS Cost Notification Agent
===========================
A backend-only automation system that:
1. Fetches AWS cost data from Datadog
2. Compares current vs last month costs
3. Detects anomalies (configurable threshold)
4. Sends weekly email reports to teams and admins
5. Teams get only their data, admins get all data
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="AWS Cost Notification Agent", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scheduler for weekly jobs
scheduler = AsyncIOScheduler()

# ==================== MODELS ====================

class Team(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    team_name: str
    aws_account_id: str
    team_email: EmailStr
    admin_emails: List[EmailStr] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TeamCreate(BaseModel):
    team_name: str
    aws_account_id: str
    team_email: EmailStr
    admin_emails: List[EmailStr] = []

class CostData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    aws_account_id: str
    team_name: str
    month: str  # YYYY-MM format
    total_cost: float
    service_breakdown: Dict[str, float] = {}
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CostAnomaly(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    aws_account_id: str
    team_name: str
    current_month: str
    current_cost: float
    previous_month: str
    previous_cost: float
    percentage_change: float
    is_anomaly: bool
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NotificationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    anomaly_threshold: float = 20.0  # Percentage increase to trigger anomaly
    schedule_day: str = "monday"  # Day of the week for weekly report
    schedule_hour: int = 9  # Hour in UTC
    global_admin_emails: List[EmailStr] = []
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NotificationConfigUpdate(BaseModel):
    anomaly_threshold: Optional[float] = None
    schedule_day: Optional[str] = None
    schedule_hour: Optional[int] = None
    global_admin_emails: Optional[List[EmailStr]] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    sender_email: Optional[str] = None

# ==================== DATADOG SERVICE ====================

class DatadogService:
    """Service to fetch AWS cost data from Datadog"""
    
    def __init__(self):
        self.api_key = os.environ.get('DATADOG_API_KEY', '')
        self.app_key = os.environ.get('DATADOG_APP_KEY', '')
        self.site = os.environ.get('DATADOG_SITE', 'datadoghq.com')
        self.base_url = f"https://api.{self.site}"
    
    async def get_cost_metrics(self, account_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Fetch AWS cost metrics from Datadog for a specific account
        Uses Datadog Metrics Query API
        """
        if not self.api_key or not self.app_key:
            logger.warning("Datadog credentials not configured, returning mock data")
            return self._generate_mock_data(account_id, start_date, end_date)
        
        try:
            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json"
            }
            
            # Query aws.cost.* metrics filtered by account
            query = f"avg:aws.cost.amortized{{account_id:{account_id}}}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    headers=headers,
                    params={
                        "from": start_date,
                        "to": end_date,
                        "query": query
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Datadog API error: {response.status_code}")
                    return self._generate_mock_data(account_id, start_date, end_date)
                    
        except Exception as e:
            logger.error(f"Error fetching from Datadog: {e}")
            return self._generate_mock_data(account_id, start_date, end_date)
    
    def _generate_mock_data(self, account_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate mock cost data for demonstration"""
        import random
        
        # Generate realistic mock data
        base_cost = random.uniform(5000, 50000)
        services = ["EC2", "RDS", "S3", "Lambda", "CloudFront", "ECS", "EKS", "DynamoDB"]
        
        service_breakdown = {}
        remaining = base_cost
        for i, service in enumerate(services[:-1]):
            if remaining <= 0:
                break
            cost = random.uniform(0, remaining * 0.4)
            service_breakdown[service] = round(cost, 2)
            remaining -= cost
        service_breakdown[services[-1]] = round(remaining, 2)
        
        return {
            "account_id": account_id,
            "total_cost": round(base_cost, 2),
            "service_breakdown": service_breakdown,
            "is_mock": True
        }

datadog_service = DatadogService()

# ==================== EMAIL SERVICE ====================

class EmailService:
    """Service to send email notifications"""
    
    async def send_team_report(self, team: Dict, cost_data: Dict, anomalies: List[Dict], config: Dict):
        """Send cost report to a specific team"""
        try:
            subject = f"AWS Cost Report - {team['team_name']} (Week of {datetime.now().strftime('%b %d')})"
            html_content = self._generate_team_email_html(team, cost_data, anomalies)
            
            await self._send_email(
                to_emails=[team['team_email']],
                subject=subject,
                html_content=html_content,
                config=config
            )
            logger.info(f"Team report sent to {team['team_email']}")
        except Exception as e:
            logger.error(f"Failed to send team report: {e}")
    
    async def send_admin_report(self, all_teams_data: List[Dict], all_anomalies: List[Dict], config: Dict):
        """Send consolidated report to admins"""
        try:
            subject = f"AWS Org Cost Summary - All {len(all_teams_data)} Accounts (Week of {datetime.now().strftime('%b %d')})"
            html_content = self._generate_admin_email_html(all_teams_data, all_anomalies)
            
            admin_emails = config.get('global_admin_emails', [])
            if admin_emails:
                await self._send_email(
                    to_emails=admin_emails,
                    subject=subject,
                    html_content=html_content,
                    config=config
                )
                logger.info(f"Admin report sent to {len(admin_emails)} admins")
        except Exception as e:
            logger.error(f"Failed to send admin report: {e}")
    
    async def _send_email(self, to_emails: List[str], subject: str, html_content: str, config: Dict):
        """Send email via SMTP"""
        smtp_host = config.get('smtp_host') or os.environ.get('SMTP_HOST', '')
        smtp_port = config.get('smtp_port') or int(os.environ.get('SMTP_PORT', 587))
        smtp_user = config.get('smtp_user') or os.environ.get('SMTP_USER', '')
        smtp_password = config.get('smtp_password') or os.environ.get('SMTP_PASSWORD', '')
        sender_email = config.get('sender_email') or os.environ.get('SENDER_EMAIL', '')
        
        if not all([smtp_host, smtp_user, smtp_password, sender_email]):
            logger.warning("SMTP not configured, logging email content instead")
            logger.info(f"Would send to: {to_emails}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Content preview: {html_content[:500]}...")
            return
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(to_emails)
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, to_emails, msg.as_string())
    
    def _generate_team_email_html(self, team: Dict, cost_data: Dict, anomalies: List[Dict]) -> str:
        """Generate HTML email for team report"""
        current_cost = cost_data.get('current_month_cost', 0)
        previous_cost = cost_data.get('previous_month_cost', 0)
        change = ((current_cost - previous_cost) / previous_cost * 100) if previous_cost > 0 else 0
        
        # Determine change indicator
        if change > 20:
            change_indicator = f'<span style="color: #dc2626; font-weight: bold;">+{change:.1f}% ⚠️ ANOMALY</span>'
        elif change > 0:
            change_indicator = f'<span style="color: #f59e0b;">+{change:.1f}%</span>'
        else:
            change_indicator = f'<span style="color: #10b981;">{change:.1f}%</span>'
        
        # Service breakdown table
        services_html = ""
        for service, cost in cost_data.get('service_breakdown', {}).items():
            prev_service_cost = cost_data.get('previous_service_breakdown', {}).get(service, 0)
            service_change = ((cost - prev_service_cost) / prev_service_cost * 100) if prev_service_cost > 0 else 0
            
            if service_change > 20:
                service_indicator = f'<span style="color: #dc2626;">+{service_change:.1f}% ⚠️</span>'
            elif service_change > 0:
                service_indicator = f'<span style="color: #f59e0b;">+{service_change:.1f}%</span>'
            else:
                service_indicator = f'<span style="color: #10b981;">{service_change:.1f}%</span>'
            
            services_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{service}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${cost:,.2f}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{service_indicator}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1f2937; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 20px; border: 1px solid #e5e7eb; }}
                .metric-card {{ background: #f9fafb; border-radius: 8px; padding: 15px; margin: 10px 0; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #1e3a5f; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th {{ background: #f3f4f6; padding: 10px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">AWS Cost Report</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">{team['team_name']} - {datetime.now().strftime('%B %Y')}</p>
                </div>
                <div class="content">
                    <div class="metric-card">
                        <div style="font-size: 14px; color: #6b7280;">Current Month Cost</div>
                        <div class="metric-value">${current_cost:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: #6b7280;">Previous Month Cost</div>
                        <div class="metric-value">${previous_cost:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div style="font-size: 14px; color: #6b7280;">Month-over-Month Change</div>
                        <div class="metric-value">{change_indicator}</div>
                    </div>
                    
                    <h3 style="margin-top: 25px; color: #1e3a5f;">Cost Breakdown by Service</h3>
                    <table>
                        <tr>
                            <th>Service</th>
                            <th style="text-align: right;">Cost</th>
                            <th style="text-align: right;">Change</th>
                        </tr>
                        {services_html}
                    </table>
                    
                    <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">
                        This report was automatically generated by AWS Cost Notification Agent.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_admin_email_html(self, all_teams_data: List[Dict], all_anomalies: List[Dict]) -> str:
        """Generate HTML email for admin consolidated report"""
        total_current = sum(t.get('current_month_cost', 0) for t in all_teams_data)
        total_previous = sum(t.get('previous_month_cost', 0) for t in all_teams_data)
        total_change = ((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0
        
        # Anomalies table
        anomalies_html = ""
        sorted_anomalies = sorted(all_anomalies, key=lambda x: x.get('percentage_change', 0), reverse=True)[:10]
        for i, anomaly in enumerate(sorted_anomalies, 1):
            anomalies_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{i}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{anomaly.get('team_name', 'N/A')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${anomaly.get('current_cost', 0):,.2f}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right; color: #dc2626;">+{anomaly.get('percentage_change', 0):.1f}%</td>
            </tr>
            """
        
        # All teams summary table
        teams_html = ""
        sorted_teams = sorted(all_teams_data, key=lambda x: x.get('current_month_cost', 0), reverse=True)
        for team_data in sorted_teams:
            change = team_data.get('percentage_change', 0)
            if change > 20:
                change_indicator = f'<span style="color: #dc2626;">+{change:.1f}% ⚠️</span>'
            elif change > 0:
                change_indicator = f'<span style="color: #f59e0b;">+{change:.1f}%</span>'
            else:
                change_indicator = f'<span style="color: #10b981;">{change:.1f}%</span>'
            
            teams_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{team_data.get('team_name', 'N/A')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{team_data.get('aws_account_id', 'N/A')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${team_data.get('current_month_cost', 0):,.2f}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${team_data.get('previous_month_cost', 0):,.2f}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{change_indicator}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1f2937; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 20px; border: 1px solid #e5e7eb; }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
                .metric-card {{ background: #f9fafb; border-radius: 8px; padding: 15px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #1e3a5f; }}
                .anomaly-section {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                th {{ background: #f3f4f6; padding: 10px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">AWS Organization Cost Summary</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">All {len(all_teams_data)} Accounts - {datetime.now().strftime('%B %Y')}</p>
                </div>
                <div class="content">
                    <div class="summary-grid">
                        <div class="metric-card">
                            <div style="font-size: 12px; color: #6b7280;">Total Current Month</div>
                            <div class="metric-value">${total_current:,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div style="font-size: 12px; color: #6b7280;">Total Previous Month</div>
                            <div class="metric-value">${total_previous:,.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div style="font-size: 12px; color: #6b7280;">Total Change</div>
                            <div class="metric-value" style="color: {'#dc2626' if total_change > 20 else '#10b981'};">{'+' if total_change > 0 else ''}{total_change:.1f}%</div>
                        </div>
                    </div>
                    
                    <div class="anomaly-section">
                        <h3 style="margin: 0 0 10px 0; color: #dc2626;">⚠️ Top Cost Anomalies ({len(all_anomalies)} detected)</h3>
                        <table>
                            <tr>
                                <th>#</th>
                                <th>Team</th>
                                <th style="text-align: right;">Current Cost</th>
                                <th style="text-align: right;">Change</th>
                            </tr>
                            {anomalies_html}
                        </table>
                    </div>
                    
                    <h3 style="margin-top: 25px; color: #1e3a5f;">All Teams Cost Summary</h3>
                    <table>
                        <tr>
                            <th>Team</th>
                            <th>Account ID</th>
                            <th style="text-align: right;">Current</th>
                            <th style="text-align: right;">Previous</th>
                            <th style="text-align: right;">Change</th>
                        </tr>
                        {teams_html}
                    </table>
                    
                    <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">
                        This consolidated report was automatically generated by AWS Cost Notification Agent.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

email_service = EmailService()

# ==================== COST ANALYZER ====================

class CostAnalyzer:
    """Analyzes cost data and detects anomalies"""
    
    async def analyze_team_costs(self, team: Dict, threshold: float = 20.0) -> Dict:
        """Analyze costs for a single team"""
        account_id = team['aws_account_id']
        
        # Get date ranges
        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
        previous_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        previous_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Fetch cost data from Datadog
        current_data = await datadog_service.get_cost_metrics(
            account_id, 
            current_month_start, 
            now.strftime("%Y-%m-%d")
        )
        previous_data = await datadog_service.get_cost_metrics(
            account_id,
            previous_month_start,
            previous_month_end
        )
        
        current_cost = current_data.get('total_cost', 0)
        previous_cost = previous_data.get('total_cost', 0)
        
        # Calculate percentage change
        if previous_cost > 0:
            percentage_change = ((current_cost - previous_cost) / previous_cost) * 100
        else:
            percentage_change = 0
        
        is_anomaly = percentage_change > threshold
        
        return {
            'team_name': team['team_name'],
            'aws_account_id': account_id,
            'current_month_cost': current_cost,
            'previous_month_cost': previous_cost,
            'percentage_change': round(percentage_change, 2),
            'is_anomaly': is_anomaly,
            'service_breakdown': current_data.get('service_breakdown', {}),
            'previous_service_breakdown': previous_data.get('service_breakdown', {}),
            'current_month': now.strftime("%Y-%m"),
            'previous_month': (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        }

cost_analyzer = CostAnalyzer()

# ==================== SCHEDULED JOB ====================

async def run_weekly_report():
    """Main scheduled job - runs weekly to fetch costs and send notifications"""
    logger.info("Starting weekly cost report generation...")
    
    try:
        # Get configuration
        config_doc = await db.notification_config.find_one({}, {"_id": 0})
        if not config_doc:
            config_doc = NotificationConfig().model_dump()
        
        threshold = config_doc.get('anomaly_threshold', 20.0)
        
        # Get all teams
        teams = await db.teams.find({}, {"_id": 0}).to_list(1000)
        if not teams:
            logger.warning("No teams configured, skipping report generation")
            return
        
        all_teams_data = []
        all_anomalies = []
        
        # Analyze each team's costs
        for team in teams:
            try:
                team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
                all_teams_data.append(team_analysis)
                
                # Send individual team report
                await email_service.send_team_report(team, team_analysis, [], config_doc)
                
                # Track anomalies
                if team_analysis['is_anomaly']:
                    anomaly = CostAnomaly(
                        aws_account_id=team['aws_account_id'],
                        team_name=team['team_name'],
                        current_month=team_analysis['current_month'],
                        current_cost=team_analysis['current_month_cost'],
                        previous_month=team_analysis['previous_month'],
                        previous_cost=team_analysis['previous_month_cost'],
                        percentage_change=team_analysis['percentage_change'],
                        is_anomaly=True
                    )
                    all_anomalies.append(anomaly.model_dump())
                    
                    # Store anomaly in DB
                    await db.anomalies.insert_one(anomaly.model_dump())
                
                # Store cost data
                cost_record = CostData(
                    aws_account_id=team['aws_account_id'],
                    team_name=team['team_name'],
                    month=team_analysis['current_month'],
                    total_cost=team_analysis['current_month_cost'],
                    service_breakdown=team_analysis['service_breakdown']
                )
                await db.cost_history.insert_one(cost_record.model_dump())
                
            except Exception as e:
                logger.error(f"Error processing team {team.get('team_name', 'unknown')}: {e}")
        
        # Send admin consolidated report
        await email_service.send_admin_report(all_teams_data, all_anomalies, config_doc)
        
        logger.info(f"Weekly report completed. Processed {len(teams)} teams, found {len(all_anomalies)} anomalies")
        
    except Exception as e:
        logger.error(f"Weekly report job failed: {e}")

# ==================== API ROUTES ====================

@api_router.get("/")
async def root():
    return {
        "message": "AWS Cost Notification Agent",
        "version": "1.0.0",
        "description": "Backend automation for AWS cost monitoring and notifications"
    }

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Team Management
@api_router.post("/teams", response_model=Team)
async def create_team(team_input: TeamCreate):
    """Add a new team with AWS account mapping"""
    team = Team(**team_input.model_dump())
    doc = team.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.teams.insert_one(doc)
    return team

@api_router.get("/teams", response_model=List[Team])
async def get_all_teams():
    """Get all configured teams"""
    teams = await db.teams.find({}, {"_id": 0}).to_list(1000)
    return teams

@api_router.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    """Get a specific team by ID"""
    team = await db.teams.find_one({"id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@api_router.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete a team"""
    result = await db.teams.delete_one({"id": team_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"message": "Team deleted successfully"}

@api_router.post("/teams/bulk")
async def bulk_create_teams(teams: List[TeamCreate]):
    """Bulk create teams from a list"""
    created_teams = []
    for team_input in teams:
        team = Team(**team_input.model_dump())
        doc = team.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.teams.insert_one(doc)
        created_teams.append(team)
    return {"message": f"Created {len(created_teams)} teams", "teams": created_teams}

# Configuration
@api_router.get("/config")
async def get_config():
    """Get notification configuration"""
    config = await db.notification_config.find_one({}, {"_id": 0})
    if not config:
        default_config = NotificationConfig()
        doc = default_config.model_dump()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.notification_config.insert_one(doc)
        return default_config
    return config

@api_router.put("/config")
async def update_config(config_update: NotificationConfigUpdate):
    """Update notification configuration"""
    update_data = {k: v for k, v in config_update.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.notification_config.update_one(
        {},
        {"$set": update_data},
        upsert=True
    )
    
    # Reschedule if schedule changed
    if 'schedule_day' in update_data or 'schedule_hour' in update_data:
        config = await db.notification_config.find_one({}, {"_id": 0})
        reschedule_weekly_job(config)
    
    return {"message": "Configuration updated successfully"}

# Cost Data
@api_router.get("/costs/history")
async def get_cost_history(
    team_name: Optional[str] = None,
    month: Optional[str] = None,
    limit: int = Query(default=100, le=1000)
):
    """Get historical cost data"""
    query = {}
    if team_name:
        query['team_name'] = team_name
    if month:
        query['month'] = month
    
    costs = await db.cost_history.find(query, {"_id": 0}).sort("fetched_at", -1).to_list(limit)
    return costs

@api_router.get("/anomalies")
async def get_anomalies(
    team_name: Optional[str] = None,
    limit: int = Query(default=50, le=500)
):
    """Get detected cost anomalies"""
    query = {}
    if team_name:
        query['team_name'] = team_name
    
    anomalies = await db.anomalies.find(query, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    return anomalies

# Manual Triggers
@api_router.post("/trigger/weekly-report")
async def trigger_weekly_report(background_tasks: BackgroundTasks):
    """Manually trigger the weekly report generation"""
    background_tasks.add_task(run_weekly_report)
    return {"message": "Weekly report generation triggered", "status": "processing"}

@api_router.post("/trigger/team-report/{team_id}")
async def trigger_team_report(team_id: str, background_tasks: BackgroundTasks):
    """Manually trigger report for a specific team"""
    team = await db.teams.find_one({"id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    async def generate_single_report():
        config_doc = await db.notification_config.find_one({}, {"_id": 0})
        if not config_doc:
            config_doc = NotificationConfig().model_dump()
        
        threshold = config_doc.get('anomaly_threshold', 20.0)
        team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
        await email_service.send_team_report(team, team_analysis, [], config_doc)
    
    background_tasks.add_task(generate_single_report)
    return {"message": f"Report triggered for team {team['team_name']}", "status": "processing"}

@api_router.get("/preview/team-report/{team_id}")
async def preview_team_report(team_id: str):
    """Preview the team report without sending email"""
    team = await db.teams.find_one({"id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    config_doc = await db.notification_config.find_one({}, {"_id": 0})
    if not config_doc:
        config_doc = NotificationConfig().model_dump()
    
    threshold = config_doc.get('anomaly_threshold', 20.0)
    team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
    
    return {
        "team": team,
        "analysis": team_analysis,
        "email_preview": email_service._generate_team_email_html(team, team_analysis, [])
    }

@api_router.get("/preview/admin-report")
async def preview_admin_report():
    """Preview the admin consolidated report without sending email"""
    teams = await db.teams.find({}, {"_id": 0}).to_list(1000)
    if not teams:
        raise HTTPException(status_code=404, detail="No teams configured")
    
    config_doc = await db.notification_config.find_one({}, {"_id": 0})
    if not config_doc:
        config_doc = NotificationConfig().model_dump()
    
    threshold = config_doc.get('anomaly_threshold', 20.0)
    
    all_teams_data = []
    all_anomalies = []
    
    for team in teams:
        team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
        all_teams_data.append(team_analysis)
        
        if team_analysis['is_anomaly']:
            all_anomalies.append({
                'team_name': team['team_name'],
                'current_cost': team_analysis['current_month_cost'],
                'percentage_change': team_analysis['percentage_change']
            })
    
    return {
        "teams_count": len(teams),
        "anomalies_count": len(all_anomalies),
        "teams_data": all_teams_data,
        "anomalies": all_anomalies,
        "email_preview": email_service._generate_admin_email_html(all_teams_data, all_anomalies)
    }

# Scheduler Status
@api_router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and next run time"""
    jobs = scheduler.get_jobs()
    job_info = []
    for job in jobs:
        job_info.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        "running": scheduler.running,
        "jobs": job_info
    }

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== SCHEDULER SETUP ====================

def reschedule_weekly_job(config: Dict):
    """Reschedule the weekly job based on configuration"""
    try:
        # Remove existing job if present
        if scheduler.get_job('weekly_cost_report'):
            scheduler.remove_job('weekly_cost_report')
        
        # Day mapping
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2,
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        day = config.get('schedule_day', 'monday').lower()
        hour = config.get('schedule_hour', 9)
        
        scheduler.add_job(
            run_weekly_report,
            CronTrigger(day_of_week=day_map.get(day, 0), hour=hour, minute=0),
            id='weekly_cost_report',
            name='Weekly Cost Report',
            replace_existing=True
        )
        
        logger.info(f"Scheduled weekly report for {day} at {hour}:00 UTC")
        
    except Exception as e:
        logger.error(f"Failed to schedule job: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    config = await db.notification_config.find_one({}, {"_id": 0})
    if not config:
        config = NotificationConfig().model_dump()
    
    reschedule_weekly_job(config)
    scheduler.start()
    logger.info("AWS Cost Notification Agent started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    client.close()
    logger.info("AWS Cost Notification Agent stopped")
