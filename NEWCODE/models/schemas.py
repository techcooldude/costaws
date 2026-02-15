"""
Pydantic Data Models
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid


class Team(BaseModel):
    """Team/AWS Account model"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    team_name: str
    aws_account_id: str
    team_email: EmailStr
    admin_emails: List[EmailStr] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeamCreate(BaseModel):
    """Create team request"""
    team_name: str
    aws_account_id: str
    team_email: EmailStr
    admin_emails: List[EmailStr] = []


class CostData(BaseModel):
    """Cost data model"""
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
    """Cost anomaly model"""
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
    """Configuration update model"""
    anomaly_threshold: Optional[float] = None
    schedule_day: Optional[str] = None
    schedule_hour: Optional[int] = None
    global_admin_emails: Optional[List[EmailStr]] = None
    ai_enabled: Optional[bool] = None
