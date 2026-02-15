"""
S3 Storage Service - Keep your original S3Storage class here
Copy the entire S3Storage class from your paste.txt file
This handles all data persistence to S3 or local files
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """
    S3-based storage for all application data.
    - Tries IAM role first (EC2/ECS)
    - Falls back to access keys from env
    - Falls back to local file storage if no AWS credentials
    """
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.local_storage_dir = Path('./data')
        self.use_s3 = False
        self.s3_client = None
        
        self._init_s3_client()
    
    def _init_s3_client(self):
        """Initialize S3 client with IAM role or access keys"""
        try:
            # First try: IAM role (no explicit credentials)
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if credentials:
                logger.info("Using IAM role for S3 access (recommended)")
                self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
                self._verify_bucket_access()
                return
            
            # Second try: Default credential chain
            try:
                self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
                self._verify_bucket_access()
                return
            except Exception:
                pass
            
            # No credentials available
            logger.warning("No AWS credentials found - using local file storage (demo mode)")
            self._setup_local_storage()
            
        except NoCredentialsError:
            logger.warning("No AWS credentials found - using local file storage")
            self._setup_local_storage()
        except Exception as e:
            logger.warning(f"S3 initialization failed: {e} - using local file storage")
            self._setup_local_storage()
    
    def _verify_bucket_access(self):
        """Verify we can access/create the S3 bucket"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.use_s3 = True
            logger.info(f"S3 bucket '{self.bucket_name}' accessible")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                try:
                    region = settings.AWS_REGION
                    if region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    self.use_s3 = True
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    self._setup_local_storage()
            else:
                logger.error(f"Bucket access error: {e}")
                self._setup_local_storage()
    
    def _setup_local_storage(self):
        """Set up local file storage as fallback"""
        self.use_s3 = False
        self.s3_client = None
        self.local_storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local storage at {self.local_storage_dir}")
    
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
    
    # Teams methods
    def get_all_teams(self) -> List[Dict]:
        data = self._get_object('teams/teams.json')
        return data.get('teams', []) if data else []
    
    def save_teams(self, teams: List[Dict]) -> bool:
        return self._put_object('teams/teams.json', {
            'teams': teams,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    
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
                'anomaly_threshold': settings.ANOMALY_THRESHOLD,
                'schedule_day': settings.SCHEDULE_DAY,
                'schedule_hour': settings.SCHEDULE_HOUR,
                'global_admin_emails': settings.get_admin_emails(),
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
