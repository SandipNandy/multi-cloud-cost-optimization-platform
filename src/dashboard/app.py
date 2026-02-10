import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

# Streamlit Dashboard
st.set_page_config(
    page_title="Cloud Cost Anomaly Dashboard",
    page_icon="💰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .critical {
        color: #DC2626;
        font-weight: bold;
    }
    .high {
        color: #EA580C;
        font-weight: bold;
    }
    .medium {
        color: #CA8A04;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">☁️ Real-Time Cloud Cost Anomaly Detection</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    api_url = st.text_input(
        "API URL",
        value="http://localhost:8000",
        help="URL of your FastAPI backend"
    )
    
    refresh_interval = st.slider(
        "Auto-refresh (seconds)",
        min_value=10,
        max_value=300,
        value=60,
        help="How often to refresh data"
    )
    
    hours_to_view = st.selectbox(
        "Time Window",
        options=[1, 6, 12, 24, 168],
        index=3,
        format_func=lambda x: f"{x} hour{'s' if x > 1 else ''}" if x < 24 else f"{x//24} day{'s' if x > 24 else ''}"
    )
    
    if st.button("🔄 Run Detection Now", type="primary"):
        with st.spinner("Running detection..."):
            try:
                response = requests.post(f"{api_url}/api/v1/detect?cloud=all")
                if response.status_code == 200:
                    st.success("Detection started!")
                else:
                    st.error("Failed to start detection")
            except Exception as e:
                st.error(f"Error: {e}")

# Main content
col1, col2, col3, col4 = st.columns(4)

try:
    # Fetch statistics
    stats_response = requests.get(f"{api_url}/api/v1/stats?hours={hours_to_view}")
    stats = stats_response.json() if stats_response.status_code == 200 else {}
    
    # Fetch anomalies
    anomalies_response = requests.get(f"{api_url}/api/v1/anomalies?limit=100&status=open")
    anomalies = anomalies_response.json() if anomalies_response.status_code == 200 else {"anomalies": []}
    
    # Metrics cards
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="Total Anomalies",
            value=stats.get('counts', {}).get('total', 0),
            delta=f"{stats.get('counts', {}).get('critical', 0)} critical"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="Estimated Monthly Savings",
            value=f"${stats.get('estimated_monthly_savings', 0):,.0f}",
            delta="Potential savings"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="By AWS",
            value=next((item['count'] for item in stats.get('by_cloud', []) if item['cloud_provider'] == 'aws'), 0),
            delta="Findings"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="Last Updated",
            value=datetime.now().strftime("%H:%M:%S"),
            delta="Real-time"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Anomalies by Severity")
        if stats.get('counts'):
            severity_data = {
                'Critical': stats['counts']['critical'],
                'High': stats['counts']['high'],
                'Medium': stats['counts']['medium']
            }
            fig = px.pie(
                values=list(severity_data.values()),
                names=list(severity_data.keys()),
                color=list(severity_data.keys()),
                color_discrete_map={
                    'Critical': '#DC2626',
                    'High': '#EA580C',
                    'Medium': '#CA8A04'
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("Anomalies by Cloud Provider")
        if stats.get('by_cloud'):
            cloud_data = pd.DataFrame(stats['by_cloud'])
            fig = px.bar(
                cloud_data,
                x='cloud_provider',
                y='count',
                color='cloud_provider',
                labels={'cloud_provider': 'Cloud', 'count': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Anomalies table
    st.subheader("Recent Anomalies")
    
    if anomalies['anomalies']:
        # Convert to DataFrame for display
        df_data = []
        for anomaly in anomalies['anomalies']:
            df_data.append({
                'ID': anomaly['id'],
                'Cloud': anomaly['cloud_provider'].upper(),
                'Resource': anomaly['resource_id'][:30] + ('...' if len(anomaly['resource_id']) > 30 else ''),
                'Type': anomaly['anomaly_type'].replace('_', ' ').title(),
                'Severity': anomaly['severity'],
                'Detected': anomaly['detected_at'].replace('T', ' ')[:19],
                'Impact': f"${anomaly.get('cost_impact', 0):,.2f}"
            })
        
        df = pd.DataFrame(df_data)
        
        # Color severity column
        def color_severity(val):
            if val == 'critical':
                return 'color: #DC2626'
            elif val == 'high':
                return 'color: #EA580C'
            elif val == 'medium':
                return 'color: #CA8A04'
            return ''
        
        styled_df = df.style.applymap(color_severity, subset=['Severity'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Detail view
        st.subheader("Anomaly Details")
        selected_id = st.selectbox(
            "Select anomaly for details",
            options=[a['id'] for a in anomalies['anomalies']],
            format_func=lambda x: f"ID {x}: {next(a['resource_id'] for a in anomalies['anomalies'] if a['id'] == x)}"
        )
        
        if selected_id:
            selected_anomaly = next(a for a in anomalies['anomalies'] if a['id'] == selected_id)
            col_detail1, col_detail2 = st.columns(2)
            
            with col_detail1:
                st.json(selected_anomaly['details'] if selected_anomaly['details'] else {})
            
            with col_detail2:
                st.markdown("### Recommended Actions")
                details = selected_anomaly.get('details', {})
                recommendation = details.get('recommendation', 'Review resource configuration')
                st.info(recommendation)
                
                if st.button("Mark as Resolved", key=f"resolve_{selected_id}"):
                    st.success("Anomaly marked as resolved (demo)")
    
    else:
        st.info("No anomalies detected in the selected time window.")
        
except Exception as e:
    st.error(f"Error connecting to API: {e}")
    st.info("Make sure the FastAPI backend is running at the specified URL.")

# Auto-refresh
st.markdown(f"<small>Auto-refreshing every {refresh_interval} seconds</small>", unsafe_allow_html=True)
st.experimental_rerun()