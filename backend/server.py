"""
AWS Cost Notification Agent with AI/LLM (S3 Storage Version)
============================================================
An intelligent backend automation system that:
1. Fetches AWS cost data from Datadog
2. Uses Gemini 3 Flash to analyze patterns and predict costs
3. Detects anomalies and explains WHY they happened
4. Provides optimization recommendations
5. Sends weekly email reports with AI insights
6. Teams get only their data, admins get all data

STORAGE: AWS S3 (no database required)
AI: Gemini 3 Flash for intelligent analysis
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import boto3
from botocore.exceptions import ClientError
import os
import logging
import json
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

# Load environment variables FIRST
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import LLM after loading env
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Create the main app
app = FastAPI(title="AWS Cost AI Agent", version="3.0.0")

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

# ==================== AI/LLM SERVICE ====================

class CostAIService:
    """
    AI-powered cost analysis using Gemini 3 Flash.
    Provides:
    - Anomaly pattern detection
    - Cost predictions
    - Optimization recommendations
    - Natural language summaries
    """
    
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY', os.environ.get('EMERGENT_LLM_KEY', ''))
        self.model = "gemini-3-flash-preview"
        self.datadog_base_url = os.environ.get('DATADOG_SITE', 'datadoghq.com')
    
    def _get_datadog_links(self, account_id: str) -> Dict[str, str]:
        """Generate Datadog dashboard links for an account"""
        base = f"https://app.{self.datadog_base_url}"
        return {
            "cost_dashboard": f"{base}/cost/overview?account_id={account_id}",
            "cost_explorer": f"{base}/cost/explorer?filter=account_id:{account_id}",
            "anomaly_monitor": f"{base}/monitors/manage?q=tag:account_id:{account_id}",
            "service_breakdown": f"{base}/cost/analytics?groupBy=service&filter=account_id:{account_id}"
        }
    
    async def analyze_cost_anomaly(self, team_data: Dict) -> Dict[str, Any]:
        """
        Analyze WHY costs changed using AI.
        Returns insights about the cost changes.
        """
        if not self.api_key:
            logger.warning("LLM API key not configured, returning basic analysis")
            return self._basic_analysis(team_data)
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"cost-analysis-{team_data.get('aws_account_id', 'unknown')}",
                system_message="""You are an AWS cost optimization expert. Analyze the provided cost data and:
1. Explain WHY costs changed (be specific about services)
2. Identify patterns or anomalies
3. Provide actionable recommendations
Keep responses concise and actionable. Use bullet points."""
            ).with_model("gemini", self.model)
            
            prompt = f"""Analyze this AWS cost data for {team_data.get('team_name', 'Unknown Team')}:

Current Month: ${team_data.get('current_month_cost', 0):,.2f}
Previous Month: ${team_data.get('previous_month_cost', 0):,.2f}
Change: {team_data.get('percentage_change', 0):.1f}%

Service Breakdown (Current):
{json.dumps(team_data.get('service_breakdown', {}), indent=2)}

Service Breakdown (Previous):
{json.dumps(team_data.get('previous_service_breakdown', {}), indent=2)}

Provide:
1. Root cause analysis (why did costs change?)
2. Top 3 cost drivers
3. Specific optimization recommendations"""

            response = await chat.send_message(UserMessage(text=prompt))
            
            return {
                "ai_analysis": response,
                "analysis_type": "gemini-3-flash",
                "datadog_links": self._get_datadog_links(team_data.get('aws_account_id', '')),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._basic_analysis(team_data)
    
    async def predict_next_month_cost(self, historical_data: List[Dict], team_name: str) -> Dict[str, Any]:
        """
        Predict next month's cost based on historical trends.
        """
        if not self.api_key or len(historical_data) < 2:
            return self._basic_prediction(historical_data)
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"cost-prediction-{team_name}",
                system_message="""You are an AWS cost forecasting expert. Based on historical cost data, predict next month's costs.
Provide a specific dollar amount prediction with confidence level and reasoning."""
            ).with_model("gemini", self.model)
            
            # Prepare historical summary
            history_summary = "\n".join([
                f"- {d.get('month', 'N/A')}: ${d.get('total_cost', 0):,.2f}"
                for d in sorted(historical_data, key=lambda x: x.get('month', ''))[-6:]
            ])
            
            prompt = f"""Based on this cost history for {team_name}, predict next month's AWS cost:

Historical Costs:
{history_summary}

Provide:
1. Predicted cost (specific dollar amount)
2. Confidence level (low/medium/high)
3. Key factors affecting the prediction
4. Potential risks that could increase costs"""

            response = await chat.send_message(UserMessage(text=prompt))
            
            return {
                "prediction": response,
                "model": "gemini-3-flash",
                "historical_months_analyzed": len(historical_data),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cost prediction failed: {e}")
            return self._basic_prediction(historical_data)
    
    async def generate_optimization_recommendations(self, all_teams_data: List[Dict]) -> Dict[str, Any]:
        """
        Generate organization-wide optimization recommendations.
        """
        if not self.api_key:
            return {"recommendations": "Configure GEMINI_API_KEY for AI recommendations"}
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id="org-optimization",
                system_message="""You are an AWS cost optimization consultant for a large organization.
Analyze cost data across multiple accounts and provide strategic recommendations.
Focus on high-impact, actionable items."""
            ).with_model("gemini", self.model)
            
            # Summarize all teams data
            total_current = sum(t.get('current_month_cost', 0) for t in all_teams_data)
            total_previous = sum(t.get('previous_month_cost', 0) for t in all_teams_data)
            
            top_spenders = sorted(all_teams_data, key=lambda x: x.get('current_month_cost', 0), reverse=True)[:10]
            top_anomalies = sorted([t for t in all_teams_data if t.get('is_anomaly')], 
                                   key=lambda x: x.get('percentage_change', 0), reverse=True)[:5]
            
            prompt = f"""Analyze this AWS Organization cost summary ({len(all_teams_data)} accounts):

Total Current Month: ${total_current:,.2f}
Total Previous Month: ${total_previous:,.2f}
Overall Change: {((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0:.1f}%

Top 10 Spending Teams:
{json.dumps([{'team': t['team_name'], 'cost': t['current_month_cost'], 'change': t['percentage_change']} for t in top_spenders], indent=2)}

Top Anomalies (cost spikes):
{json.dumps([{'team': t['team_name'], 'cost': t['current_month_cost'], 'change': t['percentage_change']} for t in top_anomalies], indent=2)}

Provide:
1. Top 5 organization-wide cost optimization opportunities
2. Teams that need immediate attention
3. Reserved Instance / Savings Plan recommendations
4. Quick wins (actions that can save money this week)"""

            response = await chat.send_message(UserMessage(text=prompt))
            
            return {
                "org_recommendations": response,
                "accounts_analyzed": len(all_teams_data),
                "total_spend": total_current,
                "anomalies_detected": len(top_anomalies),
                "model": "gemini-3-flash",
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Optimization recommendations failed: {e}")
            return {"recommendations": f"Error generating recommendations: {str(e)}"}
    
    async def generate_executive_summary(self, all_teams_data: List[Dict], all_anomalies: List[Dict]) -> str:
        """
        Generate an AI-powered executive summary for admin reports.
        """
        if not self.api_key:
            return self._basic_executive_summary(all_teams_data, all_anomalies)
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id="executive-summary",
                system_message="""You are a CFO's assistant writing cost reports. 
Write concise, executive-friendly summaries with clear action items.
Use professional language suitable for C-level executives."""
            ).with_model("gemini", self.model)
            
            total_current = sum(t.get('current_month_cost', 0) for t in all_teams_data)
            total_previous = sum(t.get('previous_month_cost', 0) for t in all_teams_data)
            
            prompt = f"""Write a brief executive summary for this AWS cost report:

Organization: {len(all_teams_data)} AWS accounts
Current Month Spend: ${total_current:,.2f}
Previous Month Spend: ${total_previous:,.2f}
Month-over-Month Change: {((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0:.1f}%
Cost Anomalies Detected: {len(all_anomalies)}

Top anomalies:
{json.dumps([{'team': a.get('team_name'), 'change': a.get('percentage_change')} for a in all_anomalies[:5]], indent=2)}

Write a 3-4 sentence executive summary highlighting:
1. Overall cost trend
2. Key concerns
3. Recommended immediate actions"""

            response = await chat.send_message(UserMessage(text=prompt))
            return response
            
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return self._basic_executive_summary(all_teams_data, all_anomalies)
    
    def _basic_analysis(self, team_data: Dict) -> Dict[str, Any]:
        """Fallback basic analysis without AI"""
        change = team_data.get('percentage_change', 0)
        current = team_data.get('service_breakdown', {})
        previous = team_data.get('previous_service_breakdown', {})
        
        # Find biggest changes
        changes = []
        for service, cost in current.items():
            prev_cost = previous.get(service, 0)
            if prev_cost > 0:
                service_change = ((cost - prev_cost) / prev_cost) * 100
                changes.append((service, service_change, cost - prev_cost))
        
        changes.sort(key=lambda x: abs(x[2]), reverse=True)
        top_changes = changes[:3]
        
        analysis = f"Cost {'increased' if change > 0 else 'decreased'} by {abs(change):.1f}%.\n\n"
        analysis += "Top cost changes:\n"
        for service, pct, diff in top_changes:
            analysis += f"• {service}: {'↑' if diff > 0 else '↓'} ${abs(diff):,.2f} ({pct:+.1f}%)\n"
        
        return {
            "ai_analysis": analysis,
            "analysis_type": "basic (configure GEMINI_API_KEY for AI analysis)",
            "datadog_links": self._get_datadog_links(team_data.get('aws_account_id', '')),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _basic_prediction(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Fallback basic prediction without AI"""
        if not historical_data:
            return {"prediction": "Insufficient data for prediction"}
        
        costs = [d.get('total_cost', 0) for d in historical_data]
        avg_cost = sum(costs) / len(costs)
        
        return {
            "prediction": f"Based on {len(costs)} months of data, estimated next month cost: ${avg_cost:,.2f}",
            "model": "basic-average",
            "historical_months_analyzed": len(costs),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _basic_executive_summary(self, all_teams_data: List[Dict], all_anomalies: List[Dict]) -> str:
        """Fallback basic executive summary"""
        total_current = sum(t.get('current_month_cost', 0) for t in all_teams_data)
        total_previous = sum(t.get('previous_month_cost', 0) for t in all_teams_data)
        change = ((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0
        
        return f"""This month's AWS spend across {len(all_teams_data)} accounts totaled ${total_current:,.2f}, 
{'an increase' if change > 0 else 'a decrease'} of {abs(change):.1f}% from last month. 
{len(all_anomalies)} accounts showed unusual cost patterns requiring attention.
Configure GEMINI_API_KEY for detailed AI-powered insights."""

# Initialize AI service
ai_service = CostAIService()

# ==================== S3 STORAGE SERVICE ====================

class S3Storage:
    """
    S3-based storage for all application data.
    Falls back to local file storage if S3 credentials not configured.
    """
    
    def __init__(self):
        self.bucket_name = os.environ.get('S3_BUCKET_NAME', 'aws-cost-agent-data')
        self.aws_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
        self.aws_secret = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
        self.use_s3 = bool(self.aws_key and self.aws_secret)
        
        self.local_storage_dir = Path('/app/backend/data')
        
        if self.use_s3:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_key,
                aws_secret_access_key=self.aws_secret,
                region_name=os.environ.get('AWS_REGION', 'us-east-1')
            )
            self._ensure_bucket_exists()
        else:
            logger.warning("S3 credentials not configured - using local file storage")
            self.local_storage_dir.mkdir(parents=True, exist_ok=True)
            self.s3_client = None
    
    def _ensure_bucket_exists(self):
        if not self.use_s3:
            return
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                try:
                    region = os.environ.get('AWS_REGION', 'us-east-1')
                    if region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
    
    def _get_local_path(self, key: str) -> Path:
        return self.local_storage_dir / key
    
    def _get_object(self, key: str) -> Optional[Dict]:
        if self.use_s3:
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                return json.loads(response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return None
                logger.error(f"Error getting {key}: {e}")
                return None
        else:
            local_path = self._get_local_path(key)
            if local_path.exists():
                try:
                    with open(local_path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error reading local file {key}: {e}")
            return None
    
    def _put_object(self, key: str, data: Dict) -> bool:
        if self.use_s3:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=json.dumps(data, indent=2, default=str),
                    ContentType='application/json'
                )
                return True
            except Exception as e:
                logger.error(f"Error putting {key}: {e}")
                return False
        else:
            local_path = self._get_local_path(key)
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                return True
            except Exception as e:
                logger.error(f"Error writing local file {key}: {e}")
                return False
    
    def _list_objects(self, prefix: str) -> List[str]:
        if self.use_s3:
            try:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                return [obj['Key'] for obj in response.get('Contents', [])]
            except Exception as e:
                logger.error(f"Error listing {prefix}: {e}")
                return []
        else:
            local_path = self._get_local_path(prefix)
            if not local_path.exists():
                return []
            try:
                files = []
                for p in local_path.rglob('*.json'):
                    rel_path = p.relative_to(self.local_storage_dir)
                    files.append(str(rel_path))
                return files
            except Exception as e:
                logger.error(f"Error listing local files {prefix}: {e}")
                return []
    
    def _delete_object(self, key: str) -> bool:
        if self.use_s3:
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception as e:
                logger.error(f"Error deleting {key}: {e}")
                return False
        else:
            local_path = self._get_local_path(key)
            try:
                if local_path.exists():
                    local_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Error deleting local file {key}: {e}")
                return False
    
    # Teams methods
    def get_all_teams(self) -> List[Dict]:
        data = self._get_object('teams/teams.json')
        return data.get('teams', []) if data else []
    
    def save_teams(self, teams: List[Dict]) -> bool:
        return self._put_object('teams/teams.json', {'teams': teams, 'updated_at': datetime.now(timezone.utc).isoformat()})
    
    def get_team_by_id(self, team_id: str) -> Optional[Dict]:
        teams = self.get_all_teams()
        for team in teams:
            if team.get('id') == team_id:
                return team
        return None
    
    def add_team(self, team: Dict) -> bool:
        teams = self.get_all_teams()
        teams.append(team)
        return self.save_teams(teams)
    
    def delete_team(self, team_id: str) -> bool:
        teams = self.get_all_teams()
        new_teams = [t for t in teams if t.get('id') != team_id]
        if len(new_teams) == len(teams):
            return False
        return self.save_teams(new_teams)
    
    # Config methods
    def get_config(self) -> Dict:
        config = self._get_object('config/notification_config.json')
        if not config:
            config = {
                'id': str(uuid.uuid4()),
                'anomaly_threshold': 20.0,
                'schedule_day': 'monday',
                'schedule_hour': 9,
                'global_admin_emails': [],
                'smtp_host': '',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'sender_email': '',
                'ai_enabled': True,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            self.save_config(config)
        return config
    
    def save_config(self, config: Dict) -> bool:
        config['updated_at'] = datetime.now(timezone.utc).isoformat()
        return self._put_object('config/notification_config.json', config)
    
    # Cost history methods
    def save_cost_record(self, cost_data: Dict) -> bool:
        year_month = cost_data.get('month', datetime.now(timezone.utc).strftime('%Y-%m'))
        year, month = year_month.split('-')
        account_id = cost_data.get('aws_account_id', 'unknown')
        key = f"costs/{year}/{month}/{account_id}.json"
        
        existing = self._get_object(key)
        if existing:
            records = existing.get('records', [])
            records.append(cost_data)
        else:
            records = [cost_data]
        
        return self._put_object(key, {
            'aws_account_id': account_id,
            'month': year_month,
            'records': records,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
    
    def get_cost_history(self, team_name: Optional[str] = None, month: Optional[str] = None, limit: int = 100) -> List[Dict]:
        all_records = []
        
        if month:
            year, mon = month.split('-')
            prefix = f"costs/{year}/{mon}/"
        else:
            prefix = "costs/"
        
        keys = self._list_objects(prefix)
        
        for key in keys:
            if key.endswith('.json'):
                data = self._get_object(key)
                if data and 'records' in data:
                    for record in data['records']:
                        if team_name and record.get('team_name') != team_name:
                            continue
                        all_records.append(record)
        
        all_records.sort(key=lambda x: x.get('fetched_at', ''), reverse=True)
        return all_records[:limit]
    
    def get_team_cost_history(self, aws_account_id: str, limit: int = 12) -> List[Dict]:
        """Get cost history for a specific account"""
        all_records = []
        keys = self._list_objects("costs/")
        
        for key in keys:
            if aws_account_id in key and key.endswith('.json'):
                data = self._get_object(key)
                if data and 'records' in data:
                    all_records.extend(data['records'])
        
        all_records.sort(key=lambda x: x.get('month', ''), reverse=True)
        return all_records[:limit]
    
    # Anomaly methods
    def save_anomaly(self, anomaly: Dict) -> bool:
        year_month = anomaly.get('current_month', datetime.now(timezone.utc).strftime('%Y-%m'))
        year, month = year_month.split('-')
        key = f"anomalies/{year}/{month}/anomalies.json"
        
        existing = self._get_object(key)
        if existing:
            anomalies = existing.get('anomalies', [])
            anomalies.append(anomaly)
        else:
            anomalies = [anomaly]
        
        return self._put_object(key, {
            'month': year_month,
            'anomalies': anomalies,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
    
    def get_anomalies(self, team_name: Optional[str] = None, limit: int = 50) -> List[Dict]:
        all_anomalies = []
        keys = self._list_objects("anomalies/")
        
        for key in keys:
            if key.endswith('.json'):
                data = self._get_object(key)
                if data and 'anomalies' in data:
                    for anomaly in data['anomalies']:
                        if team_name and anomaly.get('team_name') != team_name:
                            continue
                        all_anomalies.append(anomaly)
        
        all_anomalies.sort(key=lambda x: x.get('detected_at', ''), reverse=True)
        return all_anomalies[:limit]
    
    # AI Insights storage
    def save_ai_insight(self, insight: Dict) -> bool:
        year_month = datetime.now(timezone.utc).strftime('%Y-%m')
        year, month = year_month.split('-')
        key = f"ai_insights/{year}/{month}/insights.json"
        
        existing = self._get_object(key)
        if existing:
            insights = existing.get('insights', [])
            insights.append(insight)
        else:
            insights = [insight]
        
        return self._put_object(key, {
            'month': year_month,
            'insights': insights,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
    
    def get_ai_insights(self, limit: int = 20) -> List[Dict]:
        all_insights = []
        keys = self._list_objects("ai_insights/")
        
        for key in keys:
            if key.endswith('.json'):
                data = self._get_object(key)
                if data and 'insights' in data:
                    all_insights.extend(data['insights'])
        
        all_insights.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
        return all_insights[:limit]

# Initialize storage
storage = S3Storage()

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
    month: str
    total_cost: float
    service_breakdown: Dict[str, float] = {}
    ai_analysis: Optional[str] = None
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
    ai_explanation: Optional[str] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    ai_enabled: Optional[bool] = None

# ==================== DATADOG SERVICE ====================

class DatadogService:
    """Service to fetch AWS cost data from Datadog"""
    
    def __init__(self):
        self.api_key = os.environ.get('DATADOG_API_KEY', '')
        self.app_key = os.environ.get('DATADOG_APP_KEY', '')
        self.site = os.environ.get('DATADOG_SITE', 'datadoghq.com')
        self.base_url = f"https://api.{self.site}"
    
    async def get_cost_metrics(self, account_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        if not self.api_key or not self.app_key:
            logger.warning("Datadog credentials not configured, returning mock data")
            return self._generate_mock_data(account_id, start_date, end_date)
        
        try:
            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json"
            }
            
            query = f"avg:aws.cost.amortized{{account_id:{account_id}}}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    headers=headers,
                    params={"from": start_date, "to": end_date, "query": query}
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
        import random
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
    """Service to send email notifications with AI insights"""
    
    async def send_team_report(self, team: Dict, cost_data: Dict, ai_analysis: Dict, config: Dict):
        try:
            subject = f"🤖 AWS Cost Report - {team['team_name']} (Week of {datetime.now().strftime('%b %d')})"
            html_content = self._generate_team_email_html(team, cost_data, ai_analysis)
            
            await self._send_email(
                to_emails=[team['team_email']],
                subject=subject,
                html_content=html_content,
                config=config
            )
            logger.info(f"Team report sent to {team['team_email']}")
        except Exception as e:
            logger.error(f"Failed to send team report: {e}")
    
    async def send_admin_report(self, all_teams_data: List[Dict], all_anomalies: List[Dict], 
                                 ai_summary: str, ai_recommendations: Dict, config: Dict):
        try:
            subject = f"🤖 AWS Org Cost Summary - All {len(all_teams_data)} Accounts (Week of {datetime.now().strftime('%b %d')})"
            html_content = self._generate_admin_email_html(all_teams_data, all_anomalies, ai_summary, ai_recommendations)
            
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
        smtp_host = config.get('smtp_host') or os.environ.get('SMTP_HOST', '')
        smtp_port = config.get('smtp_port') or int(os.environ.get('SMTP_PORT', 587))
        smtp_user = config.get('smtp_user') or os.environ.get('SMTP_USER', '')
        smtp_password = config.get('smtp_password') or os.environ.get('SMTP_PASSWORD', '')
        sender_email = config.get('sender_email') or os.environ.get('SENDER_EMAIL', '')
        
        if not all([smtp_host, smtp_user, smtp_password, sender_email]):
            logger.warning("SMTP not configured, logging email content instead")
            logger.info(f"Would send to: {to_emails}")
            logger.info(f"Subject: {subject}")
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
    
    def _generate_team_email_html(self, team: Dict, cost_data: Dict, ai_analysis: Dict) -> str:
        current_cost = cost_data.get('current_month_cost', 0)
        previous_cost = cost_data.get('previous_month_cost', 0)
        change = ((current_cost - previous_cost) / previous_cost * 100) if previous_cost > 0 else 0
        
        if change > 20:
            change_indicator = f'<span style="color: #dc2626; font-weight: bold;">+{change:.1f}% ⚠️ ANOMALY</span>'
        elif change > 0:
            change_indicator = f'<span style="color: #f59e0b;">+{change:.1f}%</span>'
        else:
            change_indicator = f'<span style="color: #10b981;">{change:.1f}%</span>'
        
        # Service breakdown
        services_html = ""
        for service, cost in cost_data.get('service_breakdown', {}).items():
            prev_cost = cost_data.get('previous_service_breakdown', {}).get(service, 0)
            svc_change = ((cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0
            
            if svc_change > 20:
                svc_indicator = f'<span style="color: #dc2626;">+{svc_change:.1f}% ⚠️</span>'
            elif svc_change > 0:
                svc_indicator = f'<span style="color: #f59e0b;">+{svc_change:.1f}%</span>'
            else:
                svc_indicator = f'<span style="color: #10b981;">{svc_change:.1f}%</span>'
            
            services_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{service}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${cost:,.2f}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{svc_indicator}</td>
            </tr>"""
        
        # AI Analysis section
        ai_text = ai_analysis.get('ai_analysis', 'AI analysis not available')
        datadog_links = ai_analysis.get('datadog_links', {})
        
        links_html = ""
        if datadog_links:
            links_html = """
            <div style="margin-top: 15px; padding: 10px; background: #f0f9ff; border-radius: 8px;">
                <strong>📊 Datadog Links:</strong><br>
                <a href="{cost_dashboard}" style="color: #2563eb;">Cost Dashboard</a> | 
                <a href="{cost_explorer}" style="color: #2563eb;">Cost Explorer</a> | 
                <a href="{service_breakdown}" style="color: #2563eb;">Service Breakdown</a>
            </div>
            """.format(**datadog_links)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1f2937; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 20px; border: 1px solid #e5e7eb; }}
                .metric-card {{ background: #f9fafb; border-radius: 8px; padding: 15px; margin: 10px 0; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #1e3a5f; }}
                .ai-section {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 8px; padding: 15px; margin: 15px 0; border-left: 4px solid #f59e0b; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th {{ background: #f3f4f6; padding: 10px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">🤖 AI-Powered Cost Report</h1>
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
                    
                    <div class="ai-section">
                        <h3 style="margin: 0 0 10px 0; color: #92400e;">🧠 AI Analysis (Gemini 3 Flash)</h3>
                        <div style="white-space: pre-wrap;">{ai_text}</div>
                    </div>
                    
                    {links_html}
                    
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
                        Generated by AWS Cost AI Agent • Powered by Gemini 3 Flash
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_admin_email_html(self, all_teams_data: List[Dict], all_anomalies: List[Dict], 
                                    ai_summary: str, ai_recommendations: Dict) -> str:
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
            </tr>"""
        
        # All teams table
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
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{change_indicator}</td>
            </tr>"""
        
        # AI Recommendations
        ai_rec_text = ai_recommendations.get('org_recommendations', 'Configure GEMINI_API_KEY for AI recommendations')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1f2937; }}
                .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 20px; border: 1px solid #e5e7eb; }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
                .metric-card {{ background: #f9fafb; border-radius: 8px; padding: 15px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #1e3a5f; }}
                .ai-section {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 8px; padding: 15px; margin: 15px 0; border-left: 4px solid #f59e0b; }}
                .anomaly-section {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                th {{ background: #f3f4f6; padding: 10px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">🤖 AI-Powered Organization Cost Summary</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">All {len(all_teams_data)} Accounts - {datetime.now().strftime('%B %Y')}</p>
                </div>
                <div class="content">
                    <div class="ai-section">
                        <h3 style="margin: 0 0 10px 0; color: #92400e;">🧠 Executive Summary (AI-Generated)</h3>
                        <div style="white-space: pre-wrap;">{ai_summary}</div>
                    </div>
                    
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
                            <tr><th>#</th><th>Team</th><th style="text-align: right;">Current Cost</th><th style="text-align: right;">Change</th></tr>
                            {anomalies_html}
                        </table>
                    </div>
                    
                    <div class="ai-section">
                        <h3 style="margin: 0 0 10px 0; color: #92400e;">💡 AI Optimization Recommendations</h3>
                        <div style="white-space: pre-wrap;">{ai_rec_text}</div>
                    </div>
                    
                    <h3 style="margin-top: 25px; color: #1e3a5f;">All Teams Cost Summary</h3>
                    <table>
                        <tr><th>Team</th><th>Account ID</th><th style="text-align: right;">Current</th><th style="text-align: right;">Change</th></tr>
                        {teams_html}
                    </table>
                    
                    <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">
                        Generated by AWS Cost AI Agent • Powered by Gemini 3 Flash
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

email_service = EmailService()

# ==================== COST ANALYZER ====================

class CostAnalyzer:
    """Analyzes cost data and detects anomalies with AI assistance"""
    
    async def analyze_team_costs(self, team: Dict, threshold: float = 20.0) -> Dict:
        account_id = team['aws_account_id']
        
        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
        previous_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        previous_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        current_data = await datadog_service.get_cost_metrics(account_id, current_month_start, now.strftime("%Y-%m-%d"))
        previous_data = await datadog_service.get_cost_metrics(account_id, previous_month_start, previous_month_end)
        
        current_cost = current_data.get('total_cost', 0)
        previous_cost = previous_data.get('total_cost', 0)
        
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
    """Main scheduled job with AI analysis"""
    logger.info("Starting AI-powered weekly cost report generation...")
    
    try:
        config = storage.get_config()
        threshold = config.get('anomaly_threshold', 20.0)
        ai_enabled = config.get('ai_enabled', True)
        
        teams = storage.get_all_teams()
        if not teams:
            logger.warning("No teams configured, skipping report generation")
            return
        
        all_teams_data = []
        all_anomalies = []
        
        # Analyze each team
        for team in teams:
            try:
                team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
                
                # Get AI analysis for each team
                ai_analysis = {}
                if ai_enabled:
                    ai_analysis = await ai_service.analyze_cost_anomaly(team_analysis)
                    
                    # Get cost prediction
                    historical = storage.get_team_cost_history(team['aws_account_id'], limit=12)
                    if len(historical) >= 2:
                        prediction = await ai_service.predict_next_month_cost(historical, team['team_name'])
                        ai_analysis['prediction'] = prediction
                
                all_teams_data.append(team_analysis)
                
                # Send team report
                await email_service.send_team_report(team, team_analysis, ai_analysis, config)
                
                # Track anomalies
                if team_analysis['is_anomaly']:
                    anomaly = {
                        'id': str(uuid.uuid4()),
                        'aws_account_id': team['aws_account_id'],
                        'team_name': team['team_name'],
                        'current_month': team_analysis['current_month'],
                        'current_cost': team_analysis['current_month_cost'],
                        'previous_month': team_analysis['previous_month'],
                        'previous_cost': team_analysis['previous_month_cost'],
                        'percentage_change': team_analysis['percentage_change'],
                        'is_anomaly': True,
                        'ai_explanation': ai_analysis.get('ai_analysis', ''),
                        'detected_at': datetime.now(timezone.utc).isoformat()
                    }
                    all_anomalies.append(anomaly)
                    storage.save_anomaly(anomaly)
                
                # Save cost record
                cost_record = {
                    'id': str(uuid.uuid4()),
                    'aws_account_id': team['aws_account_id'],
                    'team_name': team['team_name'],
                    'month': team_analysis['current_month'],
                    'total_cost': team_analysis['current_month_cost'],
                    'service_breakdown': team_analysis['service_breakdown'],
                    'ai_analysis': ai_analysis.get('ai_analysis', ''),
                    'fetched_at': datetime.now(timezone.utc).isoformat()
                }
                storage.save_cost_record(cost_record)
                
            except Exception as e:
                logger.error(f"Error processing team {team.get('team_name', 'unknown')}: {e}")
        
        # Generate AI insights for admin report
        ai_summary = ""
        ai_recommendations = {}
        if ai_enabled:
            ai_summary = await ai_service.generate_executive_summary(all_teams_data, all_anomalies)
            ai_recommendations = await ai_service.generate_optimization_recommendations(all_teams_data)
            
            # Save AI insights
            storage.save_ai_insight({
                'type': 'weekly_report',
                'executive_summary': ai_summary,
                'recommendations': ai_recommendations,
                'teams_analyzed': len(all_teams_data),
                'anomalies_detected': len(all_anomalies),
                'generated_at': datetime.now(timezone.utc).isoformat()
            })
        
        # Send admin consolidated report
        await email_service.send_admin_report(all_teams_data, all_anomalies, ai_summary, ai_recommendations, config)
        
        logger.info(f"Weekly report completed. Processed {len(teams)} teams, found {len(all_anomalies)} anomalies")
        
    except Exception as e:
        logger.error(f"Weekly report job failed: {e}")

# ==================== API ROUTES ====================

@api_router.get("/")
async def root():
    return {
        "message": "AWS Cost AI Agent",
        "version": "3.0.0",
        "ai_model": "Gemini 3 Flash",
        "storage": "AWS S3" if storage.use_s3 else "Local File (Demo)",
        "features": ["Cost Analysis", "Anomaly Detection", "AI Predictions", "Optimization Recommendations"]
    }

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": "S3" if storage.use_s3 else "Local",
        "ai_configured": bool(ai_service.api_key)
    }

# Team Management
@api_router.post("/teams")
async def create_team(team_input: TeamCreate):
    team = Team(**team_input.model_dump())
    team_dict = team.model_dump()
    team_dict['created_at'] = team_dict['created_at'].isoformat()
    storage.add_team(team_dict)
    return team

@api_router.get("/teams")
async def get_all_teams():
    return storage.get_all_teams()

@api_router.get("/teams/{team_id}")
async def get_team(team_id: str):
    team = storage.get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@api_router.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    success = storage.delete_team(team_id)
    if not success:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"message": "Team deleted successfully"}

@api_router.post("/teams/bulk")
async def bulk_create_teams(teams: List[TeamCreate]):
    created_teams = []
    for team_input in teams:
        team = Team(**team_input.model_dump())
        team_dict = team.model_dump()
        team_dict['created_at'] = team_dict['created_at'].isoformat()
        storage.add_team(team_dict)
        created_teams.append(team)
    return {"message": f"Created {len(created_teams)} teams", "teams": created_teams}

# Configuration
@api_router.get("/config")
async def get_config():
    return storage.get_config()

@api_router.put("/config")
async def update_config(config_update: NotificationConfigUpdate):
    current_config = storage.get_config()
    update_data = {k: v for k, v in config_update.model_dump().items() if v is not None}
    current_config.update(update_data)
    storage.save_config(current_config)
    
    if 'schedule_day' in update_data or 'schedule_hour' in update_data:
        reschedule_weekly_job(current_config)
    
    return {"message": "Configuration updated successfully"}

# Cost Data
@api_router.get("/costs/history")
async def get_cost_history(team_name: Optional[str] = None, month: Optional[str] = None, limit: int = Query(default=100, le=1000)):
    return storage.get_cost_history(team_name, month, limit)

@api_router.get("/anomalies")
async def get_anomalies(team_name: Optional[str] = None, limit: int = Query(default=50, le=500)):
    return storage.get_anomalies(team_name, limit)

# AI Endpoints
@api_router.get("/ai/insights")
async def get_ai_insights(limit: int = Query(default=20, le=100)):
    """Get historical AI insights"""
    return storage.get_ai_insights(limit)

@api_router.post("/ai/analyze/{team_id}")
async def analyze_team_with_ai(team_id: str):
    """Run AI analysis for a specific team"""
    team = storage.get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    config = storage.get_config()
    threshold = config.get('anomaly_threshold', 20.0)
    
    team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
    ai_analysis = await ai_service.analyze_cost_anomaly(team_analysis)
    
    # Get prediction
    historical = storage.get_team_cost_history(team['aws_account_id'], limit=12)
    prediction = await ai_service.predict_next_month_cost(historical, team['team_name'])
    
    return {
        "team": team,
        "cost_analysis": team_analysis,
        "ai_analysis": ai_analysis,
        "prediction": prediction
    }

@api_router.get("/ai/recommendations")
async def get_org_recommendations():
    """Get AI-powered organization-wide recommendations"""
    teams = storage.get_all_teams()
    if not teams:
        raise HTTPException(status_code=404, detail="No teams configured")
    
    config = storage.get_config()
    threshold = config.get('anomaly_threshold', 20.0)
    
    all_teams_data = []
    for team in teams:
        team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
        all_teams_data.append(team_analysis)
    
    recommendations = await ai_service.generate_optimization_recommendations(all_teams_data)
    return recommendations

# Manual Triggers
@api_router.post("/trigger/weekly-report")
async def trigger_weekly_report(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_weekly_report)
    return {"message": "AI-powered weekly report generation triggered", "status": "processing"}

@api_router.post("/trigger/team-report/{team_id}")
async def trigger_team_report(team_id: str, background_tasks: BackgroundTasks):
    team = storage.get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    async def generate_single_report():
        config = storage.get_config()
        threshold = config.get('anomaly_threshold', 20.0)
        team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
        ai_analysis = await ai_service.analyze_cost_anomaly(team_analysis)
        await email_service.send_team_report(team, team_analysis, ai_analysis, config)
    
    background_tasks.add_task(generate_single_report)
    return {"message": f"AI report triggered for team {team['team_name']}", "status": "processing"}

@api_router.get("/preview/team-report/{team_id}")
async def preview_team_report(team_id: str):
    team = storage.get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    config = storage.get_config()
    threshold = config.get('anomaly_threshold', 20.0)
    team_analysis = await cost_analyzer.analyze_team_costs(team, threshold)
    ai_analysis = await ai_service.analyze_cost_anomaly(team_analysis)
    
    return {
        "team": team,
        "analysis": team_analysis,
        "ai_analysis": ai_analysis,
        "email_preview": email_service._generate_team_email_html(team, team_analysis, ai_analysis)
    }

@api_router.get("/preview/admin-report")
async def preview_admin_report():
    teams = storage.get_all_teams()
    if not teams:
        raise HTTPException(status_code=404, detail="No teams configured")
    
    config = storage.get_config()
    threshold = config.get('anomaly_threshold', 20.0)
    
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
    
    ai_summary = await ai_service.generate_executive_summary(all_teams_data, all_anomalies)
    ai_recommendations = await ai_service.generate_optimization_recommendations(all_teams_data)
    
    return {
        "teams_count": len(teams),
        "anomalies_count": len(all_anomalies),
        "ai_summary": ai_summary,
        "ai_recommendations": ai_recommendations,
        "teams_data": all_teams_data,
        "anomalies": all_anomalies
    }

# Scheduler Status
@api_router.get("/scheduler/status")
async def get_scheduler_status():
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
        "jobs": job_info,
        "ai_model": "gemini-3-flash-preview",
        "ai_configured": bool(ai_service.api_key)
    }

@api_router.get("/storage/info")
async def get_storage_info():
    return {
        "type": "AWS S3" if storage.use_s3 else "Local File (Demo Mode)",
        "bucket": storage.bucket_name if storage.use_s3 else str(storage.local_storage_dir),
        "s3_configured": storage.use_s3,
        "ai_configured": bool(ai_service.api_key),
        "ai_model": "gemini-3-flash-preview"
    }

# Include router
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
    try:
        if scheduler.get_job('weekly_cost_report'):
            scheduler.remove_job('weekly_cost_report')
        
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
            name='Weekly AI Cost Report',
            replace_existing=True
        )
        
        logger.info(f"Scheduled AI-powered weekly report for {day} at {hour}:00 UTC")
        
    except Exception as e:
        logger.error(f"Failed to schedule job: {e}")

@app.on_event("startup")
async def startup_event():
    config = storage.get_config()
    reschedule_weekly_job(config)
    scheduler.start()
    logger.info(f"AWS Cost AI Agent started (AI: {'Gemini 3 Flash' if ai_service.api_key else 'Not configured'})")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("AWS Cost AI Agent stopped")
