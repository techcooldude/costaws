"""
Vertex AI Service with Service Account Authentication
Replaces AI Studio API key approach
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Vertex AI imports
from google.cloud import aiplatform
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content

from app.config import settings

logger = logging.getLogger(__name__)


class VertexAIService:
    """
    Enterprise-grade AI service using Vertex AI with Service Account authentication.
    No API keys needed - uses GCP IAM for security.
    """
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION
        self.model_name = settings.VERTEX_AI_MODEL
        self.credentials = None
        self.model = None
        self.initialized = False
        
        self._initialize()
    
    def _initialize(self):
        """Initialize Vertex AI with Service Account credentials"""
        try:
            # Load credentials from service account file
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                    self.credentials = service_account.Credentials.from_service_account_file(
                        settings.GOOGLE_APPLICATION_CREDENTIALS,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                    logger.info("✓ Loaded GCP Service Account credentials")
                else:
                    logger.error(f"Service account file not found: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
                    return
            else:
                # Try Application Default Credentials (ADC)
                logger.info("Using Application Default Credentials (ADC)")
                self.credentials = None  # Will use ADC
            
            # Initialize Vertex AI
            vertexai.init(
                project=self.project_id,
                location=self.location,
                credentials=self.credentials
            )
            
            # Initialize model
            self.model = GenerativeModel(self.model_name)
            self.initialized = True
            
            logger.info(f"✓ Vertex AI initialized: {self.model_name} in {self.location}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self.initialized = False
    
    async def _generate_content(self, prompt: str, system_instruction: str = "") -> str:
        """Generate content using Vertex AI"""
        if not self.initialized:
            logger.warning("Vertex AI not initialized, returning empty response")
            return ""
        
        try:
            # Combine system instruction and prompt
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            
            # Generate content
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Vertex AI generation error: {e}")
            return ""
    
    async def analyze_cost_anomaly(self, team_data: Dict) -> Dict[str, Any]:
        """Analyze WHY costs changed using AI"""
        if not self.initialized:
            return self._basic_analysis(team_data)
        
        try:
            system_instruction = """You are an AWS cost optimization expert. Analyze the provided cost data and:
1. Explain WHY costs changed (be specific about services)
2. Identify patterns or anomalies
3. Provide actionable recommendations
Keep responses concise and actionable. Use bullet points."""
            
            prompt = f"""Analyze this AWS cost data for {team_data.get('team_name', 'Unknown Team')}:

Current Month: ${team_data.get('current_month_cost', 0):,.2f}
Previous Month: ${team_data.get('previous_month_cost', 0):,.2f}
Change: {team_data.get('percentage_change', 0):.1f}%

Service Breakdown (Current):
{self._format_dict(team_data.get('service_breakdown', {}))}

Service Breakdown (Previous):
{self._format_dict(team_data.get('previous_service_breakdown', {}))}

Provide:
1. Root cause analysis (why did costs change?)
2. Top 3 cost drivers
3. Specific optimization recommendations"""

            response = await self._generate_content(prompt, system_instruction)
            
            if response:
                return {
                    "ai_analysis": response,
                    "analysis_type": "vertex-ai-gemini",
                    "model": self.model_name,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                return self._basic_analysis(team_data)
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._basic_analysis(team_data)
    
    async def predict_next_month_cost(self, historical_data: List[Dict], team_name: str) -> Dict[str, Any]:
        """Predict next month's cost based on historical trends"""
        if not self.initialized or len(historical_data) < 2:
            return self._basic_prediction(historical_data)
        
        try:
            system_instruction = """You are an AWS cost forecasting expert. Based on historical cost data, predict next month's costs.
Provide a specific dollar amount prediction with confidence level and reasoning."""
            
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

            response = await self._generate_content(prompt, system_instruction)
            
            if response:
                return {
                    "prediction": response,
                    "model": self.model_name,
                    "historical_months_analyzed": len(historical_data),
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                return self._basic_prediction(historical_data)
                
        except Exception as e:
            logger.error(f"Cost prediction failed: {e}")
            return self._basic_prediction(historical_data)
    
    async def generate_optimization_recommendations(self, all_teams_data: List[Dict]) -> Dict[str, Any]:
        """Generate organization-wide optimization recommendations"""
        if not self.initialized:
            return {"recommendations": "Vertex AI not configured"}
        
        try:
            system_instruction = """You are an AWS cost optimization consultant for a large organization.
Analyze cost data across multiple accounts and provide strategic recommendations.
Focus on high-impact, actionable items."""
            
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
{self._format_list([{'team': t['team_name'], 'cost': t['current_month_cost'], 'change': t['percentage_change']} for t in top_spenders])}

Top Anomalies (cost spikes):
{self._format_list([{'team': t['team_name'], 'cost': t['current_month_cost'], 'change': t['percentage_change']} for t in top_anomalies])}

Provide:
1. Top 5 organization-wide cost optimization opportunities
2. Teams that need immediate attention
3. Reserved Instance / Savings Plan recommendations
4. Quick wins (actions that can save money this week)"""

            response = await self._generate_content(prompt, system_instruction)
            
            if response:
                return {
                    "org_recommendations": response,
                    "accounts_analyzed": len(all_teams_data),
                    "total_spend": total_current,
                    "anomalies_detected": len(top_anomalies),
                    "model": self.model_name,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {"recommendations": "Failed to generate recommendations"}
                
        except Exception as e:
            logger.error(f"Optimization recommendations failed: {e}")
            return {"recommendations": f"Error: {str(e)}"}
    
    async def generate_executive_summary(self, all_teams_data: List[Dict], all_anomalies: List[Dict]) -> str:
        """Generate an AI-powered executive summary"""
        if not self.initialized:
            return self._basic_executive_summary(all_teams_data, all_anomalies)
        
        try:
            system_instruction = """You are a CFO's assistant writing cost reports. 
Write concise, executive-friendly summaries with clear action items.
Use professional language suitable for C-level executives."""
            
            total_current = sum(t.get('current_month_cost', 0) for t in all_teams_data)
            total_previous = sum(t.get('previous_month_cost', 0) for t in all_teams_data)
            
            prompt = f"""Write a brief executive summary for this AWS cost report:

Organization: {len(all_teams_data)} AWS accounts
Current Month Spend: ${total_current:,.2f}
Previous Month Spend: ${total_previous:,.2f}
Month-over-Month Change: {((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0:.1f}%
Cost Anomalies Detected: {len(all_anomalies)}

Top anomalies:
{self._format_list([{'team': a.get('team_name'), 'change': a.get('percentage_change')} for a in all_anomalies[:5]])}

Write a 3-4 sentence executive summary highlighting:
1. Overall cost trend
2. Key concerns
3. Recommended immediate actions"""

            response = await self._generate_content(prompt, system_instruction)
            return response if response else self._basic_executive_summary(all_teams_data, all_anomalies)
            
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return self._basic_executive_summary(all_teams_data, all_anomalies)
    
    def _format_dict(self, data: Dict) -> str:
        """Format dictionary for prompt"""
        import json
        return json.dumps(data, indent=2)
    
    def _format_list(self, data: List) -> str:
        """Format list for prompt"""
        import json
        return json.dumps(data, indent=2)
    
    def _basic_analysis(self, team_data: Dict) -> Dict[str, Any]:
        """Fallback basic analysis without AI"""
        change = team_data.get('percentage_change', 0)
        current = team_data.get('service_breakdown', {})
        previous = team_data.get('previous_service_breakdown', {})
        
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
            "analysis_type": "basic (Vertex AI not configured)",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _basic_prediction(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Fallback basic prediction"""
        if not historical_data:
            return {"prediction": "Insufficient data"}
        
        costs = [d.get('total_cost', 0) for d in historical_data]
        avg_cost = sum(costs) / len(costs)
        
        return {
            "prediction": f"Estimated next month: ${avg_cost:,.2f} (based on {len(costs)} months average)",
            "model": "basic-average",
            "historical_months_analyzed": len(costs),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _basic_executive_summary(self, all_teams_data: List[Dict], all_anomalies: List[Dict]) -> str:
        """Fallback basic executive summary"""
        total_current = sum(t.get('current_month_cost', 0) for t in all_teams_data)
        total_previous = sum(t.get('previous_month_cost', 0) for t in all_teams_data)
        change = ((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0
        
        return f"""AWS spend across {len(all_teams_data)} accounts: ${total_current:,.2f} this month, 
{'up' if change > 0 else 'down'} {abs(change):.1f}% from last month (${total_previous:,.2f}). 
{len(all_anomalies)} accounts showed unusual patterns. 
Configure Vertex AI for detailed AI insights."""
