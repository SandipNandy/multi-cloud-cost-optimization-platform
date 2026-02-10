from fastapi import APIRouter, BackgroundTasks, Query
from datetime import datetime, timedelta
import json
from src.detectors.aws_detector import AWSDetector
from src.detectors.azure_detector import AzureDetector
from src.detectors.gcp_detector import GCPDetector
import psycopg2
from psycopg2.extras import RealDictCursor
import os

router = APIRouter(prefix="/api/v1")

@router.post("/detect")
async def trigger_detection(
    cloud: str = Query("all", enum=["aws", "azure", "gcp", "all"]),
    background_tasks: BackgroundTasks = None
):
    """Trigger immediate anomaly detection"""
    
    async def run_detection(cloud_provider: str):
        if cloud_provider == "aws":
            detector = AWSDetector()
        elif cloud_provider == "azure":
            detector = AzureDetector()
        elif cloud_provider == "gcp":
            detector = GCPDetector()
        else:
            return
        
        findings = detector.detect_anomalies()
        return findings
    
    if cloud == "all":
        tasks = []
        for cloud_provider in ["aws", "azure", "gcp"]:
            if background_tasks:
                background_tasks.add_task(run_detection, cloud_provider)
            else:
                findings = await run_detection(cloud_provider)
                tasks.append({"cloud": cloud_provider, "findings": findings})
        return {"status": "detection_started", "clouds": ["aws", "azure", "gcp"]}
    else:
        if background_tasks:
            background_tasks.add_task(run_detection, cloud)
            return {"status": "detection_started", "cloud": cloud}
        else:
            findings = await run_detection(cloud)
            return {"status": "complete", "cloud": cloud, "findings_count": len(findings)}

@router.get("/anomalies")
async def get_anomalies(
    cloud: str = None,
    severity: str = None,
    status: str = "open",
    limit: int = 100
):
    """Get detected anomalies"""
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'cloud_cost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
    
    query = "SELECT * FROM cost_anomalies WHERE 1=1"
    params = []
    
    if cloud:
        query += " AND cloud_provider = %s"
        params.append(cloud)
    
    if severity:
        query += " AND severity = %s"
        params.append(severity)
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY detected_at DESC LIMIT %s"
    params.append(limit)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        anomalies = cur.fetchall()
    
    # Parse JSON details
    for anomaly in anomalies:
        if anomaly['details']:
            anomaly['details'] = json.loads(anomaly['details'])
    
    conn.close()
    
    return {
        "count": len(anomalies),
        "anomalies": anomalies,
        "summary": {
            "critical": len([a for a in anomalies if a['severity'] == 'critical']),
            "high": len([a for a in anomalies if a['severity'] == 'high']),
            "medium": len([a for a in anomalies if a['severity'] == 'medium'])
        }
    }

@router.get("/stats")
async def get_stats(hours: int = 24):
    """Get statistics for the last N hours"""
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'cloud_cost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Total anomalies
        cur.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
                   COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
                   COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium
            FROM cost_anomalies 
            WHERE detected_at >= %s
        """, (since,))
        counts = cur.fetchone()
        
        # By cloud provider
        cur.execute("""
            SELECT cloud_provider, COUNT(*) as count
            FROM cost_anomalies 
            WHERE detected_at >= %s
            GROUP BY cloud_provider
        """, (since,))
        by_cloud = cur.fetchall()
        
        # By anomaly type
        cur.execute("""
            SELECT anomaly_type, COUNT(*) as count
            FROM cost_anomalies 
            WHERE detected_at >= %s
            GROUP BY anomaly_type
        """, (since,))
        by_type = cur.fetchall()
        
        # Estimated savings
        cur.execute("""
            SELECT COALESCE(SUM(cost_impact), 0) as total_savings
            FROM cost_anomalies 
            WHERE detected_at >= %s AND status = 'open'
        """, (since,))
        savings = cur.fetchone()
    
    conn.close()
    
    return {
        "time_period_hours": hours,
        "since": since.isoformat(),
        "counts": counts,
        "by_cloud": by_cloud,
        "by_type": by_type,
        "estimated_monthly_savings": savings['total_savings'] * 30 / hours if hours > 0 else 0
    }