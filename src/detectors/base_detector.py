import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from google.cloud import billing_v1
import psycopg2
from psycopg2.extras import RealDictCursor

class BaseDetector:
    """Base class for all cloud detectors"""
    
    def __init__(self):
        self.db_conn = self._get_db_connection()
        self.critical_threshold = float(os.getenv('CRITICAL_THRESHOLD', '1000'))  # $1000/day spike
        self.high_threshold = float(os.getenv('HIGH_THRESHOLD', '500'))  # $500/day spike
        
    def _get_db_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'cloud_cost'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
    
    def detect_anomalies(self) -> List[Dict]:
        """Main detection method to be implemented by subclasses"""
        raise NotImplementedError
    
    def save_finding(self, finding: Dict):
        """Save detection to database"""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO cost_anomalies 
                (cloud_provider, resource_id, resource_type, anomaly_type, 
                 detected_at, cost_impact, severity, details, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open')
                RETURNING id
            """, (
                finding['cloud_provider'],
                finding['resource_id'],
                finding['resource_type'],
                finding['anomaly_type'],
                datetime.utcnow(),
                finding.get('cost_impact', 0),
                finding.get('severity', 'medium'),
                json.dumps(finding.get('details', {}))
            ))
            self.db_conn.commit()
            return cur.fetchone()['id']
    
    def trigger_alert(self, finding: Dict):
        """Trigger alert based on severity"""
        if finding.get('severity') == 'critical':
            self._send_slack_alert(finding)
            self._create_jira_ticket(finding)
        elif finding.get('severity') == 'high':
            self._send_slack_alert(finding)
    
    def _send_slack_alert(self, finding: Dict):
        """Send Slack alert"""
        from src.alerting.slack_alert import send_slack_alert
        send_slack_alert(finding)
    
    def _create_jira_ticket(self, finding: Dict):
        """Create Jira ticket for critical issues"""
        # Implementation for Jira integration
        pass