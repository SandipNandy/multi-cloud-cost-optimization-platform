from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import uvicorn
from .routes import router
from src.detectors.aws_detector import AWSDetector
from src.detectors.azure_detector import AzureDetector
from src.detectors.gcp_detector import GCPDetector

app = FastAPI(title="Cloud Cost Anomaly Detection MVP", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Global detector instances
detectors = {
    'aws': AWSDetector(),
    'azure': AzureDetector(),
    'gcp': GCPDetector()
}

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    # Start background detection task
    asyncio.create_task(periodic_detection())

async def periodic_detection():
    """Run detection every 5 minutes"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        await run_all_detections()

async def run_all_detections():
    """Run all cloud detectors"""
    for cloud, detector in detectors.items():
        try:
            findings = await asyncio.to_thread(detector.detect_anomalies)
            print(f"[{datetime.utcnow()}] {cloud}: Found {len(findings)} anomalies")
        except Exception as e:
            print(f"[{datetime.utcnow()}] Error in {cloud} detector: {e}")

@app.get("/")
async def root():
    return {
        "service": "Cloud Cost Anomaly Detection MVP",
        "status": "running",
        "endpoints": {
            "detect": "/api/v1/detect",
            "anomalies": "/api/v1/anomalies",
            "dashboard": "/dashboard"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)