import requests
import json
import os
from datetime import datetime

def send_slack_alert(finding: dict):
    """Send real-time Slack alert for anomalies"""
    
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set, skipping Slack alert")
        return
    
    # Severity colors
    colors = {
        'critical': '#dc2626',
        'high': '#ea580c',
        'medium': '#ca8a04'
    }
    
    # Create Slack message
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Cloud Cost Anomaly Detected",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Cloud:*\n{finding['cloud_provider'].upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n:{finding['severity']}: {finding['severity'].upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Resource:*\n`{finding['resource_id']}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{finding['anomaly_type'].replace('_', ' ').title()}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Potential Impact:* ${finding.get('cost_impact', 0):,.2f}/month"
                }
            }
        ]
    }
    
    # Add details if available
    if finding.get('details'):
        details = finding['details']
        recommendation = details.get('recommendation', 'Please investigate this resource.')
        
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommendation:*\n{recommendation}"
            }
        })
    
    # Add dashboard link
    dashboard_url = os.getenv('DASHBOARD_URL', 'http://localhost:8501')
    message["blocks"].append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View in Dashboard",
                    "emoji": True
                },
                "url": dashboard_url,
                "style": "primary"
            }
        ]
    })
    
    # Send to Slack
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(message),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code != 200:
            print(f"Failed to send Slack alert: {response.status_code}")
    except Exception as e:
        print(f"Error sending Slack alert: {e}")