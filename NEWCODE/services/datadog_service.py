"""
Datadog Service - Keep your original DatadogService class here
Copy the entire DatadogService class from your paste.txt file
This handles fetching AWS cost data from Datadog API
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)


class DatadogService:
    """
    Service to fetch AWS cost data from Datadog Cloud Cost Management API
    """
    
    def __init__(self):
        self.api_key = settings.DATADOG_API_KEY
        self.app_key = settings.DATADOG_APP_KEY
        self.site = settings.DATADOG_SITE
        self.base_url = f"https://api.{self.site}"
    
    def _to_epoch(self, dt: datetime) -> int:
        """Convert datetime to epoch seconds"""
        return int(dt.timestamp())
    
    async def get_cost_metrics(self, account_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Fetch cost data from Datadog Cloud Cost Management API.
        
        Args:
            account_id: AWS account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Cost data with total and service breakdown
        """
        if not self.api_key or not self.app_key:
            logger.warning("Datadog credentials not configured, returning mock data")
            return self._generate_mock_data(account_id, start_date, end_date)
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            start_epoch = self._to_epoch(start_dt)
            end_epoch = self._to_epoch(end_dt)
            
            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try Cloud Cost Management API
                cost_data = await self._fetch_cloud_cost(client, headers, account_id, start_epoch, end_epoch)
                
                if cost_data:
                    return cost_data
                
                # Fallback to mock data
                return self._generate_mock_data(account_id, start_date, end_date)
                    
        except Exception as e:
            logger.error(f"Error fetching from Datadog: {e}")
            return self._generate_mock_data(account_id, start_date, end_date)
    
    async def _fetch_cloud_cost(self, client: httpx.AsyncClient, headers: Dict, 
                                 account_id: str, start_epoch: int, end_epoch: int) -> Optional[Dict]:
        """Fetch from Cloud Cost Management API (v2)"""
        try:
            url = f"{self.base_url}/api/v2/cost_by_org"
            
            params = {
                "start_month": datetime.fromtimestamp(start_epoch, tz=timezone.utc).strftime("%Y-%m"),
                "end_month": datetime.fromtimestamp(end_epoch, tz=timezone.utc).strftime("%Y-%m"),
                "view": "sub_org"
            }
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_cloud_cost_response(data, account_id)
            else:
                logger.warning(f"Cloud Cost API returned {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Cloud Cost API error: {e}")
            return None
    
    def _parse_cloud_cost_response(self, data: Dict, account_id: str) -> Dict:
        """Parse Cloud Cost Management API response"""
        try:
            total_cost = 0
            service_breakdown = {}
            
            for org_data in data.get('data', []):
                attributes = org_data.get('attributes', {})
                org_name = attributes.get('org_name', '')
                
                if account_id in org_name or not account_id:
                    charges = attributes.get('charges', [])
                    for charge in charges:
                        charge_type = charge.get('charge_type', 'Other')
                        cost = charge.get('cost', 0)
                        total_cost += cost
                        service_breakdown[charge_type] = service_breakdown.get(charge_type, 0) + cost
            
            if total_cost > 0:
                return {
                    "account_id": account_id,
                    "total_cost": round(total_cost, 2),
                    "service_breakdown": {k: round(v, 2) for k, v in service_breakdown.items()},
                    "source": "datadog_cloud_cost",
                    "is_mock": False
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing cost response: {e}")
            return None
    
    def _generate_mock_data(self, account_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate mock cost data for testing"""
        import random
        
        base_cost = random.uniform(1000, 50000)
        
        services = {
            "EC2": base_cost * 0.4,
            "RDS": base_cost * 0.25,
            "S3": base_cost * 0.15,
            "Lambda": base_cost * 0.10,
            "CloudWatch": base_cost * 0.05,
            "Other": base_cost * 0.05
        }
        
        return {
            "account_id": account_id,
            "total_cost": round(sum(services.values()), 2),
            "service_breakdown": {k: round(v, 2) for k, v in services.items()},
            "source": "mock_data",
            "is_mock": True
        }
