# System Architecture

## Overview
```mermaid
graph TB
    subgraph "Cloud Providers"
        A[AWS Cost Explorer]
        B[Azure Cost Management]
        C[GCP Billing Export]
    end
    
    subgraph "Detection Engine"
        D[AWS Detector]
        E[Azure Detector]
        F[GCP Detector]
    end
    
    subgraph "Core Platform"
        G[FastAPI Backend]
        H[(PostgreSQL)]
        I[Streamlit Dashboard]
        J[Slack Alerts]
    end
    
    A --> D
    B --> E
    C --> F
    
    D --> G
    E --> G
    F --> G
    
    G --> H
    G --> I
    G --> J
    
    subgraph "External Systems"
        K[Jira/ServiceNow]
        L[Email]
        M[Teams]
    end
    
    J --> K
    J --> L
    J --> M