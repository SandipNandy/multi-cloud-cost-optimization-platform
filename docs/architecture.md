graph LR
    A[AWS CloudWatch] --> B[Lambda Detector]
    C[Azure Monitor] --> D[Azure Function]
    E[GCP Cloud Logging] --> F[Cloud Function]
    
    B --> G[Central API]
    D --> G
    F --> G
    
    G --> H[(PostgreSQL)]
    G --> I[Slack Alert]
    G --> J[Dashboard]