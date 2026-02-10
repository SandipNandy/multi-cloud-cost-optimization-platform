import boto3
from datetime import datetime, timedelta
from .base_detector import BaseDetector
import os

class AWSDetector(BaseDetector):
    """Real-time AWS cost anomaly detector"""
    
    def __init__(self):
        super().__init__()
        self.session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.ec2 = self.session.client('ec2')
        self.rds = self.session.client('rds')
        self.cloudwatch = self.session.client('cloudwatch')
        self.cost_explorer = self.session.client('ce')
    
    def detect_anomalies(self) -> List[Dict]:
        """Run all AWS detection rules"""
        findings = []
        
        # 1. Detect idle EC2 instances
        findings.extend(self._detect_idle_ec2())
        
        # 2. Detect unattached EBS volumes
        findings.extend(self._detect_unattached_ebs())
        
        # 3. Detect idle RDS instances
        findings.extend(self._detect_idle_rds())
        
        # 4. Detect cost spikes
        findings.extend(self._detect_cost_spikes())
        
        # Save and alert
        for finding in findings:
            finding_id = self.save_finding(finding)
            finding['id'] = finding_id
            self.trigger_alert(finding)
        
        return findings
    
    def _detect_idle_ec2(self) -> List[Dict]:
        """Detect EC2 instances with low CPU utilization"""
        findings = []
        
        # Get all running instances
        response = self.ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance.get('InstanceType', 'unknown')
                
                # Get CPU utilization for last 7 days
                cpu_stats = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=datetime.utcnow() - timedelta(days=7),
                    EndTime=datetime.utcnow(),
                    Period=86400,  # 1 day
                    Statistics=['Average']
                )
                
                if cpu_stats['Datapoints']:
                    avg_cpu = sum([dp['Average'] for dp in cpu_stats['Datapoints']]) / len(cpu_stats['Datapoints'])
                    
                    if avg_cpu < 5:  # Less than 5% average CPU
                        findings.append({
                            'cloud_provider': 'aws',
                            'resource_id': instance_id,
                            'resource_type': 'ec2',
                            'anomaly_type': 'idle_resource',
                            'severity': 'high',
                            'cost_impact': self._estimate_ec2_cost(instance_type),
                            'details': {
                                'average_cpu': round(avg_cpu, 2),
                                'instance_type': instance_type,
                                'recommendation': 'Consider stopping or downsizing this instance'
                            }
                        })
        
        return findings
    
    def _detect_unattached_ebs(self) -> List[Dict]:
        """Detect EBS volumes not attached to any instance"""
        findings = []
        
        response = self.ec2.describe_volumes(
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
        
        for volume in response['Volumes']:
            volume_id = volume['VolumeId']
            size_gb = volume['Size']
            
            # Check if volume creation date > 7 days (not newly created)
            create_time = volume['CreateTime']
            age_days = (datetime.utcnow() - create_time.replace(tzinfo=None)).days
            
            if age_days > 7:
                findings.append({
                    'cloud_provider': 'aws',
                    'resource_id': volume_id,
                    'resource_type': 'ebs',
                    'anomaly_type': 'orphaned_resource',
                    'severity': 'medium',
                    'cost_impact': size_gb * 0.10,  # Approx $0.10/GB-month
                    'details': {
                        'size_gb': size_gb,
                        'age_days': age_days,
                        'recommendation': 'Delete this unused volume'
                    }
                })
        
        return findings
    
    def _detect_idle_rds(self) -> List[Dict]:
        """Detect idle RDS instances"""
        findings = []
        
        response = self.rds.describe_db_instances()
        
        for db_instance in response['DBInstances']:
            db_id = db_instance['DBInstanceIdentifier']
            engine = db_instance['Engine']
            
            # Get CPU utilization for last 7 days
            cpu_stats = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=datetime.utcnow() - timedelta(days=7),
                EndTime=datetime.utcnow(),
                Period=86400,
                Statistics=['Average']
            )
            
            if cpu_stats['Datapoints']:
                avg_cpu = sum([dp['Average'] for dp in cpu_stats['Datapoints']]) / len(cpu_stats['Datapoints'])
                
                if avg_cpu < 2:  # Less than 2% average CPU for RDS
                    findings.append({
                        'cloud_provider': 'aws',
                        'resource_id': db_id,
                        'resource_type': 'rds',
                        'anomaly_type': 'idle_resource',
                        'severity': 'high',
                        'details': {
                            'average_cpu': round(avg_cpu, 2),
                            'engine': engine,
                            'recommendation': 'Consider stopping or downsizing this database'
                        }
                    })
        
        return findings
    
    def _detect_cost_spikes(self) -> List[Dict]:
        """Detect daily cost spikes using Cost Explorer"""
        findings = []
        
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        response = self.cost_explorer.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        # Analyze daily costs for spikes
        daily_costs = {}
        for result in response['ResultsByTime']:
            date = result['TimePeriod']['Start']
            total = float(result['Total']['UnblendedCost']['Amount'])
            daily_costs[date] = total
        
        # Calculate average and detect spikes
        if len(daily_costs) > 7:
            last_7_days = list(daily_costs.values())[-7:]
            avg_cost = sum(last_7_days) / len(last_7_days)
            latest_cost = last_7_days[-1]
            
            if latest_cost > avg_cost * 1.5:  # 50% increase
                findings.append({
                    'cloud_provider': 'aws',
                    'resource_id': 'daily_spend',
                    'resource_type': 'account',
                    'anomaly_type': 'cost_spike',
                    'severity': 'critical' if latest_cost > self.critical_threshold else 'high',
                    'cost_impact': latest_cost - avg_cost,
                    'details': {
                        'average_daily_cost': round(avg_cost, 2),
                        'current_daily_cost': round(latest_cost, 2),
                        'increase_percentage': round(((latest_cost - avg_cost) / avg_cost) * 100, 2),
                        'date': list(daily_costs.keys())[-1]
                    }
                })
        
        return findings
    
    def _estimate_ec2_cost(self, instance_type: str) -> float:
        """Simple EC2 cost estimation"""
        # Simplified cost mapping (real implementation would use AWS Pricing API)
        cost_map = {
            't2.micro': 0.0116 * 24 * 30,  # ~$8.35/month
            't2.small': 0.023 * 24 * 30,   # ~$16.56/month
            't2.medium': 0.0464 * 24 * 30, # ~$33.41/month
            'm5.large': 0.096 * 24 * 30,   # ~$69.12/month
            'm5.xlarge': 0.192 * 24 * 30,  # ~$138.24/month
        }
        return cost_map.get(instance_type, 50.0)  # Default $50/month