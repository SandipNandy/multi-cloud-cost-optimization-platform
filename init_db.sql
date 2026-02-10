-- Cloud Cost Anomaly Detection Database Schema
-- This file runs automatically when PostgreSQL container starts
-- Create database if it doesn't exist
SELECT 'CREATE DATABASE cloud_cost'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cloud_cost')\gexec

\c cloud_cost;

-- Anomalies table
CREATE TABLE IF NOT EXISTS cost_anomalies (
    id SERIAL PRIMARY KEY,
    cloud_provider VARCHAR(10) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cost_impact DECIMAL(10,2) DEFAULT 0,
    severity VARCHAR(20) NOT NULL,
    details JSONB,
    status VARCHAR(20) DEFAULT 'open',
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    CONSTRAINT valid_status CHECK (status IN ('open', 'investigating', 'resolved', 'false_positive'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_anomalies_detected ON cost_anomalies(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_status ON cost_anomalies(status);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON cost_anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_cloud ON cost_anomalies(cloud_provider);

-- Stats table for daily aggregates
CREATE TABLE IF NOT EXISTS daily_stats (
    date DATE PRIMARY KEY,
    total_anomalies INTEGER DEFAULT 0,
    critical_anomalies INTEGER DEFAULT 0,
    estimated_savings DECIMAL(10,2) DEFAULT 0,
    aws_anomalies INTEGER DEFAULT 0,
    azure_anomalies INTEGER DEFAULT 0,
    gcp_anomalies INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for testing (optional)
INSERT INTO cost_anomalies (cloud_provider, resource_id, resource_type, anomaly_type, severity, cost_impact, details)
VALUES 
('aws', 'i-1234567890abcdef0', 'ec2', 'idle_resource', 'high', 85.50, '{"average_cpu": 3.2, "instance_type": "t2.large", "recommendation": "Consider downsizing to t2.small"}'),
('aws', 'vol-abcdef1234567890', 'ebs', 'orphaned_resource', 'medium', 24.00, '{"size_gb": 100, "age_days": 15, "recommendation": "Delete unused volume"}'),
('azure', 'vm-12345', 'vm', 'idle_resource', 'high', 120.00, '{"average_cpu": 4.5, "vm_size": "Standard_D2s_v3", "recommendation": "Stop VM during non-business hours"}')
ON CONFLICT DO NOTHING;

-- Create view for dashboard
CREATE OR REPLACE VIEW vw_anomalies_summary AS
SELECT 
    DATE(detected_at) as detection_date,
    cloud_provider,
    severity,
    COUNT(*) as anomaly_count,
    SUM(cost_impact) as total_impact
FROM cost_anomalies
WHERE status = 'open'
GROUP BY DATE(detected_at), cloud_provider, severity;

-- Create function to update daily stats
CREATE OR REPLACE FUNCTION update_daily_stats()
RETURNS void AS $$
BEGIN
    INSERT INTO daily_stats (date, total_anomalies, critical_anomalies, estimated_savings, aws_anomalies, azure_anomalies, gcp_anomalies)
    SELECT 
        CURRENT_DATE,
        COUNT(*) as total_anomalies,
        COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_anomalies,
        COALESCE(SUM(cost_impact), 0) as estimated_savings,
        COUNT(CASE WHEN cloud_provider = 'aws' THEN 1 END) as aws_anomalies,
        COUNT(CASE WHEN cloud_provider = 'azure' THEN 1 END) as azure_anomalies,
        COUNT(CASE WHEN cloud_provider = 'gcp' THEN 1 END) as gcp_anomalies
    FROM cost_anomalies
    WHERE DATE(detected_at) = CURRENT_DATE
    ON CONFLICT (date) DO UPDATE SET
        total_anomalies = EXCLUDED.total_anomalies,
        critical_anomalies = EXCLUDED.critical_anomalies,
        estimated_savings = EXCLUDED.estimated_savings,
        aws_anomalies = EXCLUDED.aws_anomalies,
        azure_anomalies = EXCLUDED.azure_anomalies,
        gcp_anomalies = EXCLUDED.gcp_anomalies,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE cloud_cost TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Output confirmation
SELECT '✅ Database initialized successfully!' as status;
