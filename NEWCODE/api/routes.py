"""
API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from datetime import datetime, timezone

from app.models.schemas import Team, TeamCreate, NotificationConfigUpdate
from app.api.dependencies import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/teams", response_model=Team)
async def create_team(team: TeamCreate, request: Request):
    """Register a new AWS account to monitor"""
    storage = request.app.state.storage
    
    # Check if team already exists
    existing_teams = storage.get_all_teams()
    if any(t['aws_account_id'] == team.aws_account_id for t in existing_teams):
        raise HTTPException(status_code=400, detail="AWS account already registered")
    
    new_team = Team(
        team_name=team.team_name,
        aws_account_id=team.aws_account_id,
        team_email=team.team_email,
        admin_emails=team.admin_emails
    )
    
    if storage.add_team(new_team.model_dump()):
        return new_team
    
    raise HTTPException(status_code=500, detail="Failed to create team")


@router.get("/teams", response_model=List[Team])
async def list_teams(request: Request):
    """List all registered teams"""
    storage = request.app.state.storage
    teams = storage.get_all_teams()
    return [Team(**t) for t in teams]


@router.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str, request: Request):
    """Get a specific team by ID"""
    storage = request.app.state.storage
    team = storage.get_team_by_id(team_id)
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return Team(**team)


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str, request: Request):
    """Delete a team"""
    storage = request.app.state.storage
    
    if storage.delete_team(team_id):
        return {"message": "Team deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Team not found")


@router.get("/costs")
async def get_cost_history(
    request: Request,
    team_name: Optional[str] = None,
    month: Optional[str] = None,
    limit: int = 100
):
    """Get cost history"""
    storage = request.app.state.storage
    costs = storage.get_cost_history(team_name=team_name, month=month, limit=limit)
    return {"costs": costs, "count": len(costs)}


@router.get("/anomalies")
async def get_anomalies(
    request: Request,
    team_name: Optional[str] = None,
    limit: int = 50
):
    """Get detected cost anomalies"""
    storage = request.app.state.storage
    anomalies = storage.get_anomalies(team_name=team_name, limit=limit)
    return {"anomalies": anomalies, "count": len(anomalies)}


@router.get("/config")
async def get_config(request: Request):
    """Get current notification configuration"""
    storage = request.app.state.storage
    return storage.get_config()


@router.post("/config")
async def update_config(config: NotificationConfigUpdate, request: Request):
    """Update notification configuration"""
    storage = request.app.state.storage
    current_config = storage.get_config()
    
    # Update only provided fields
    if config.anomaly_threshold is not None:
        current_config['anomaly_threshold'] = config.anomaly_threshold
    if config.schedule_day is not None:
        current_config['schedule_day'] = config.schedule_day
    if config.schedule_hour is not None:
        current_config['schedule_hour'] = config.schedule_hour
    if config.global_admin_emails is not None:
        current_config['global_admin_emails'] = config.global_admin_emails
    if config.ai_enabled is not None:
        current_config['ai_enabled'] = config.ai_enabled
    
    if storage.save_config(current_config):
        return {"message": "Configuration updated", "config": current_config}
    
    raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.post("/analyze/trigger")
async def trigger_analysis(request: Request):
    """Manually trigger cost analysis (for testing)"""
    from app.main import analyze_and_notify
    
    try:
        await analyze_and_notify()
        return {"message": "Analysis triggered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
