#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for AWS Cost AI Agent
Tests all REST API endpoints with mock data support
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

class AWSCostAgentTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_team_ids = []
        
    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    expected_status: int = 200) -> tuple[bool, Any]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, f"Unsupported method: {method}"
            
            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = response.text
                
            return success, response_data
            
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def test_basic_endpoints(self):
        """Test basic info and health endpoints"""
        print("🔍 Testing Basic Endpoints...")
        
        # Test root endpoint
        success, data = self.make_request('GET', '/')
        self.log_test(
            "GET /api/ - Agent info endpoint",
            success,
            f"Version: {data.get('version', 'N/A')}, AI Model: {data.get('ai_model', 'N/A')}" if success else "Failed to get agent info",
            data
        )
        
        # Test health check
        success, data = self.make_request('GET', '/health')
        ai_configured = data.get('ai_configured', False) if success else False
        storage_type = data.get('storage', 'Unknown') if success else 'Unknown'
        self.log_test(
            "GET /api/health - Health check with AI status",
            success,
            f"Status: {data.get('status', 'Unknown')}, AI: {'✅' if ai_configured else '❌'}, Storage: {storage_type}" if success else "Health check failed",
            data
        )
        
        # Test storage info
        success, data = self.make_request('GET', '/storage/info')
        self.log_test(
            "GET /api/storage/info - Storage configuration",
            success,
            f"Type: {data.get('type', 'Unknown')}, S3: {'✅' if data.get('s3_configured', False) else '❌'}" if success else "Storage info failed",
            data
        )
        
        # Test scheduler status
        success, data = self.make_request('GET', '/scheduler/status')
        running = data.get('running', False) if success else False
        jobs_count = len(data.get('jobs', [])) if success else 0
        self.log_test(
            "GET /api/scheduler/status - Scheduler status and next run",
            success,
            f"Running: {'✅' if running else '❌'}, Jobs: {jobs_count}" if success else "Scheduler status failed",
            data
        )

    def test_team_management(self):
        """Test team CRUD operations"""
        print("👥 Testing Team Management...")
        
        # Test get all teams (initially empty)
        success, data = self.make_request('GET', '/teams')
        initial_teams_count = len(data) if success and isinstance(data, list) else 0
        self.log_test(
            "GET /api/teams - List all teams (initial)",
            success,
            f"Found {initial_teams_count} existing teams" if success else "Failed to list teams",
            data
        )
        
        # Test create single team
        test_team = {
            "team_name": "Test Platform Team",
            "aws_account_id": "123456789012",
            "team_email": "platform@testcompany.com",
            "admin_emails": ["admin@testcompany.com"]
        }
        
        success, data = self.make_request('POST', '/teams', test_team, 200)
        team_id = data.get('id') if success else None
        if team_id:
            self.created_team_ids.append(team_id)
        self.log_test(
            "POST /api/teams - Create single team",
            success,
            f"Created team with ID: {team_id}" if success else "Failed to create team",
            data
        )
        
        # Test bulk create teams
        bulk_teams = [
            {
                "team_name": "Test DevOps Team",
                "aws_account_id": "234567890123",
                "team_email": "devops@testcompany.com",
                "admin_emails": ["devops-admin@testcompany.com"]
            },
            {
                "team_name": "Test Data Science Team",
                "aws_account_id": "345678901234",
                "team_email": "datascience@testcompany.com",
                "admin_emails": ["ds-admin@testcompany.com"]
            }
        ]
        
        success, data = self.make_request('POST', '/teams/bulk', bulk_teams, 200)
        if success and 'teams' in data:
            for team in data['teams']:
                if 'id' in team:
                    self.created_team_ids.append(team['id'])
        created_count = len(data.get('teams', [])) if success else 0
        self.log_test(
            "POST /api/teams/bulk - Bulk create teams",
            success,
            f"Created {created_count} teams in bulk" if success else "Failed to bulk create teams",
            data
        )
        
        # Test get all teams (after creation)
        success, data = self.make_request('GET', '/teams')
        final_teams_count = len(data) if success and isinstance(data, list) else 0
        self.log_test(
            "GET /api/teams - List all teams (after creation)",
            success,
            f"Found {final_teams_count} teams total" if success else "Failed to list teams after creation",
            data
        )
        
        # Test get specific team
        if self.created_team_ids:
            test_team_id = self.created_team_ids[0]
            success, data = self.make_request('GET', f'/teams/{test_team_id}')
            team_name = data.get('team_name', 'Unknown') if success else 'Unknown'
            self.log_test(
                "GET /api/teams/{id} - Get specific team",
                success,
                f"Retrieved team: {team_name}" if success else "Failed to get specific team",
                data
            )
        else:
            self.log_test(
                "GET /api/teams/{id} - Get specific team",
                False,
                "No team ID available for testing",
                None
            )

    def test_configuration(self):
        """Test configuration endpoints"""
        print("⚙️ Testing Configuration...")
        
        # Test get config
        success, data = self.make_request('GET', '/config')
        threshold = data.get('anomaly_threshold', 'Unknown') if success else 'Unknown'
        schedule_day = data.get('schedule_day', 'Unknown') if success else 'Unknown'
        self.log_test(
            "GET /api/config - Get notification config",
            success,
            f"Threshold: {threshold}%, Schedule: {schedule_day}" if success else "Failed to get config",
            data
        )
        
        # Test update config
        config_update = {
            "anomaly_threshold": 25.0,
            "schedule_day": "tuesday",
            "schedule_hour": 10,
            "global_admin_emails": ["admin@testcompany.com"],
            "ai_enabled": True
        }
        
        success, data = self.make_request('PUT', '/config', config_update, 200)
        self.log_test(
            "PUT /api/config - Update config (threshold, schedule, admin emails)",
            success,
            "Configuration updated successfully" if success else "Failed to update config",
            data
        )

    def test_ai_endpoints(self):
        """Test AI-powered analysis endpoints"""
        print("🤖 Testing AI Endpoints...")
        
        # Test AI insights
        success, data = self.make_request('GET', '/ai/insights')
        insights_count = len(data) if success and isinstance(data, list) else 0
        self.log_test(
            "GET /api/ai/insights - Historical AI insights",
            success,
            f"Found {insights_count} AI insights" if success else "Failed to get AI insights",
            data
        )
        
        # Test organization-wide AI recommendations
        success, data = self.make_request('GET', '/ai/recommendations')
        has_recommendations = 'org_recommendations' in data or 'recommendations' in data if success else False
        self.log_test(
            "GET /api/ai/recommendations - Organization-wide AI recommendations",
            success,
            f"AI recommendations: {'✅' if has_recommendations else '❌'}" if success else "Failed to get AI recommendations",
            data
        )
        
        # Test AI analysis for specific team
        if self.created_team_ids:
            test_team_id = self.created_team_ids[0]
            success, data = self.make_request('POST', f'/ai/analyze/{test_team_id}')
            has_analysis = 'ai_analysis' in data if success else False
            self.log_test(
                "POST /api/ai/analyze/{team_id} - AI analysis for team",
                success,
                f"AI analysis generated: {'✅' if has_analysis else '❌'}" if success else "Failed to generate AI analysis",
                data
            )
        else:
            self.log_test(
                "POST /api/ai/analyze/{team_id} - AI analysis for team",
                False,
                "No team ID available for testing",
                None
            )

    def test_cost_and_anomaly_endpoints(self):
        """Test cost history and anomaly detection endpoints"""
        print("💰 Testing Cost & Anomaly Endpoints...")
        
        # Test cost history
        success, data = self.make_request('GET', '/costs/history')
        history_count = len(data) if success and isinstance(data, list) else 0
        self.log_test(
            "GET /api/costs/history - Get cost history",
            success,
            f"Found {history_count} cost records" if success else "Failed to get cost history",
            data
        )
        
        # Test anomalies
        success, data = self.make_request('GET', '/anomalies')
        anomalies_count = len(data) if success and isinstance(data, list) else 0
        self.log_test(
            "GET /api/anomalies - Get detected anomalies",
            success,
            f"Found {anomalies_count} anomalies" if success else "Failed to get anomalies",
            data
        )

    def test_report_endpoints(self):
        """Test report generation and preview endpoints"""
        print("📊 Testing Report Endpoints...")
        
        # Test admin report preview
        success, data = self.make_request('GET', '/preview/admin-report')
        has_summary = 'ai_summary' in data if success else False
        teams_count = data.get('teams_count', 0) if success else 0
        self.log_test(
            "GET /api/preview/admin-report - Preview admin consolidated report",
            success,
            f"Teams: {teams_count}, AI Summary: {'✅' if has_summary else '❌'}" if success else "Failed to preview admin report",
            data
        )
        
        # Test team report preview
        if self.created_team_ids:
            test_team_id = self.created_team_ids[0]
            success, data = self.make_request('GET', f'/preview/team-report/{test_team_id}')
            has_email_preview = 'email_preview' in data if success else False
            self.log_test(
                "GET /api/preview/team-report/{id} - Preview team email report",
                success,
                f"Email preview generated: {'✅' if has_email_preview else '❌'}" if success else "Failed to preview team report",
                data
            )
        else:
            self.log_test(
                "GET /api/preview/team-report/{id} - Preview team email report",
                False,
                "No team ID available for testing",
                None
            )
        
        # Test trigger weekly report
        success, data = self.make_request('POST', '/trigger/weekly-report')
        triggered = 'processing' in data.get('status', '') if success else False
        self.log_test(
            "POST /api/trigger/weekly-report - Trigger weekly report generation",
            success,
            f"Weekly report triggered: {'✅' if triggered else '❌'}" if success else "Failed to trigger weekly report",
            data
        )
        
        # Test trigger single team report
        if self.created_team_ids:
            test_team_id = self.created_team_ids[0]
            success, data = self.make_request('POST', f'/trigger/team-report/{test_team_id}')
            triggered = 'processing' in data.get('status', '') if success else False
            self.log_test(
                "POST /api/trigger/team-report/{id} - Trigger single team report",
                success,
                f"Team report triggered: {'✅' if triggered else '❌'}" if success else "Failed to trigger team report",
                data
            )
        else:
            self.log_test(
                "POST /api/trigger/team-report/{id} - Trigger single team report",
                False,
                "No team ID available for testing",
                None
            )

    def test_cleanup(self):
        """Clean up created test data"""
        print("🧹 Cleaning up test data...")
        
        for team_id in self.created_team_ids:
            success, data = self.make_request('DELETE', f'/teams/{team_id}')
            self.log_test(
                f"DELETE /api/teams/{team_id} - Delete team",
                success,
                "Team deleted successfully" if success else "Failed to delete team",
                data
            )

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting AWS Cost AI Agent Backend Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Run test suites
            self.test_basic_endpoints()
            self.test_team_management()
            self.test_configuration()
            self.test_ai_endpoints()
            self.test_cost_and_anomaly_endpoints()
            self.test_report_endpoints()
            
            # Wait a moment for background tasks
            print("⏳ Waiting for background tasks to complete...")
            time.sleep(3)
            
            # Cleanup
            self.test_cleanup()
            
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error during testing: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0%")
        print(f"Duration: {duration:.2f} seconds")
        
        # Show failed tests
        failed_tests = [t for t in self.test_results if not t['success']]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  • {test['test_name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test AWS Cost AI Agent Backend')
    parser.add_argument('--url', default='http://localhost:8001', 
                       help='Base URL for the API (default: http://localhost:8001)')
    
    args = parser.parse_args()
    
    tester = AWSCostAgentTester(args.url)
    success = tester.run_all_tests()
    
    # Save detailed results
    results_file = '/app/test_reports/backend_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'summary': {
                'total_tests': tester.tests_run,
                'passed_tests': tester.tests_passed,
                'failed_tests': tester.tests_run - tester.tests_passed,
                'success_rate': (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
                'test_url': args.url
            },
            'detailed_results': tester.test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())