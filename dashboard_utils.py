import pandas as pd
from datetime import datetime
from streamlit_echarts import st_echarts
import streamlit as st
from streamlit_shadcn_ui import card
import plotly.graph_objects as go
from st_aggrid import AgGrid

# Define color constants for status and sentiment
STATUS_COLORS = {
    "Rejected": "#FF4B4B",      # Red
    "Applied": "#FFD700",       # Yellow
    "Not Applied": "#1E90FF",   # Blue
    "No Response": "#FFA500",   # Orange
    "Offered": "#4CAF50",       # Green
    "Interviewing": "#9C27B0",  # Purple
    "Interviewed - Rejected": "#800000",   # Maroon
    "Interviewed - Withdrew": "#800000"   # Maroon
}

SENTIMENT_COLORS = {
    "Positive": "#000080",      # Navy
    "Neutral": "#808080",       # Grey
    "Negative": "#800000"       # Maroon
}

def get_status_chart(status_counts):
    """Create ECharts configuration for status distribution donut chart."""
    return {
        "title": {
            "text": "Application Status Distribution",
            "left": "center"
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a} <br/>{b}: {c} ({d}%)"
        },
        "legend": {
            "orient": "horizontal",
            "bottom": 0,
            "left": "center"
        },
        "series": [{
            "name": "Status",
            "type": "pie",
            "radius": ["40%", "70%"],  # Creates donut chart
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 10,  # Rounded corners
                "borderColor": "#fff",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "position": "inside"
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            },
            "data": [
                {
                    "value": count,
                    "name": status,
                    "itemStyle": {"color": STATUS_COLORS.get(status, "#808080")}  # Default to gray if status not found
                }
                for status, count in status_counts.items()
            ]
        }]
    }

def get_sentiment_chart(sentiment_counts):
    """Create ECharts configuration for sentiment distribution donut chart."""
    return {
        "title": {
            "text": "Application Sentiment Distribution",
            "left": "center"
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a} <br/>{b}: {c} ({d}%)"
        },
        "legend": {
            "orient": "horizontal",
            "bottom": 0,
            "left": "center"
        },
        "series": [{
            "name": "Sentiment",
            "type": "pie",
            "radius": ["40%", "70%"],  # Creates donut chart
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 10,  # Rounded corners
                "borderColor": "#fff",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "position": "inside"
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            },
            "data": [
                {
                    "value": count,
                    "name": sentiment,
                    "itemStyle": {"color": SENTIMENT_COLORS.get(sentiment, "#808080")}  # Default to gray if sentiment not found
                }
                for sentiment, count in sentiment_counts.items()
            ]
        }]
    }

def get_timeline_chart(daily_applications):
    """Create ECharts configuration for cumulative applications over time line chart."""
    # Convert index to datetime and sort
    daily_applications.index = pd.to_datetime(daily_applications.index)
    daily_applications = daily_applications.sort_index()
    
    # Create date range from April 28, 2025 to today
    start_date = pd.to_datetime('2025-04-28')
    end_date = pd.Timestamp.now()
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create a Series with all dates
    all_dates = pd.Series(0, index=date_range)
    
    # Merge with actual data
    merged = all_dates.combine(daily_applications, max, fill_value=0)
    
    # Calculate cumulative sum
    cumulative = merged.cumsum()
    
    return {
        "title": {
            "text": "Jobs Saved Over Time",
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": "Date: {b}<br/>Jobs: {c}"
        },
        "xAxis": {
            "type": "category",
            "data": merged.index.strftime('%Y-%m-%d').tolist(),
            "axisLabel": {
                "rotate": 45
            }
        },
        "yAxis": {
            "type": "value",
            "name": "Number of Jobs"
        },
        "series": [
            {
                "name": "Cumulative Jobs",
                "type": "line",
                "data": cumulative.values.tolist(),
                "smooth": True,
                "areaStyle": {
                    "opacity": 0.3
                },
                "lineStyle": {
                    "width": 3
                },
                "itemStyle": {
                    "color": "#1f77b4"
                }
            },
            {
                "name": "Daily Jobs",
                "type": "scatter",
                "data": merged.values.tolist(),
                "symbolSize": 8,
                "itemStyle": {
                    "color": "#ff7f0e"
                }
            }
        ],
        "legend": {
            "data": ["Cumulative Jobs", "Daily Jobs"],
            "top": 30
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "15%",
            "containLabel": True
        }
    }

def get_company_chart(jobs_df):
    """Create ECharts configuration for top 10 companies with stacked status bars."""
    if jobs_df.empty:
        return None

    # Get top 10 companies by total applications
    top_companies = jobs_df['company_name'].value_counts().head(10).index.tolist()
    
    # Filter data for top companies
    top_companies_data = jobs_df[jobs_df['company_name'].isin(top_companies)]
    
    # Get unique statuses
    statuses = top_companies_data['status'].unique().tolist()
    
    # Create data series for each status
    series = []
    for status in statuses:
        # Count applications by company for this status
        status_counts = top_companies_data[top_companies_data['status'] == status].groupby('company_name').size()
        # Create a series for this status with int conversion
        series.append({
            "name": status,
            "type": "bar",
            "stack": "total",
            "data": [int(status_counts.get(company, 0)) for company in top_companies],  # Convert to int
            "itemStyle": {
                "borderRadius": [8, 8, 8, 8],  # Rounded corners for all sides
                "borderWidth": 0,
                "color": STATUS_COLORS.get(status, "#808080")  # Default to gray if status not found
            }
        })
    
    return {
        "title": {
            "text": "Top 10 Companies by Application Status",
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "shadow"
            }
        },
        "legend": {
            "data": statuses,
            "top": 30
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "3%",
            "containLabel": True
        },
        "xAxis": {
            "type": "value",
            "name": "Number of Applications"
        },
        "yAxis": {
            "type": "category",
            "data": top_companies,
            "axisLabel": {
                "interval": 0
            },
            "inverse": True # This will show the highest count at the top
        },
        "series": series
    }

def get_job_titles_chart(jobs_df):
    """Create ECharts configuration for top 10 job titles with stacked status bars."""
    if jobs_df.empty:
        return None

    # Get top 10 job titles by total applications and sort in descending order
    title_counts = jobs_df['job_title'].value_counts()
    top_titles = title_counts.head(10).index.tolist()
    
    # Filter data for top titles
    top_titles_data = jobs_df[jobs_df['job_title'].isin(top_titles)]
    
    # Get unique statuses
    statuses = top_titles_data['status'].unique().tolist()
    
    # Create data series for each status
    series = []
    for status in statuses:
        # Count applications by job title for this status
        status_counts = top_titles_data[top_titles_data['status'] == status].groupby('job_title').size()
        # Create a series for this status with int conversion
        series.append({
            "name": status,
            "type": "bar",
            "stack": "total",
            "data": [int(status_counts.get(title, 0)) for title in top_titles],  # Convert to int
            "itemStyle": {
                "borderRadius": [8, 8, 8, 8],  # Rounded corners for all sides
                "borderWidth": 0,
                "color": STATUS_COLORS.get(status, "#808080")  # Default to gray if status not found
            }
        })
    
    return {
        "title": {
            "text": "Top 10 Job Titles by Application Status",
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "shadow"
            }
        },
        "legend": {
            "data": statuses,
            "top": 30
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "3%",
            "containLabel": True
        },
        "xAxis": {
            "type": "value",
            "name": "Number of Applications"
        },
        "yAxis": {
            "type": "category",
            "data": top_titles,
            "axisLabel": {
                "interval": 0
            },
            "inverse": True  # This will show the highest count at the top
        },
        "series": series
    }

def calculate_metrics(jobs_df):
    """Calculate key metrics for the dashboard."""
    total_applications = len(jobs_df)
    
    # Calculate average applications per day
    if len(jobs_df) > 0:
        date_diff = (datetime.now() - jobs_df['date_added'].min()).days
        avg_per_day = round(total_applications / date_diff, 1) if date_diff > 0 else 0
        
        # Calculate average applications per week
        avg_per_week = round(avg_per_day * 7, 1)
        
        # Calculate applications in last 7 days
        last_7_days = datetime.now() - pd.Timedelta(days=7)
        recent_applications = len(jobs_df[jobs_df['date_added'] >= last_7_days])
        interview_count = len(jobs_df[jobs_df['status'] == 'Interviewing'])
    else:
        avg_per_day = 0
        avg_per_week = 0
        recent_applications = 0
        interview_count = 0
    
    # Get most common status
    most_common_status = jobs_df['status'].mode()[0] if not jobs_df.empty else "N/A"
    
    return {
        "total_applications": total_applications,
        "avg_per_day": avg_per_day,
        "avg_per_week": avg_per_week,
        "recent_applications": recent_applications,
        "most_common_status": most_common_status,
        "interview_count": interview_count
    }

def prepare_dashboard_data(jobs_df):
    """Prepare all data needed for the dashboard."""
    if jobs_df.empty:
        return None
    
    # Convert date_added to datetime if it's not already
    jobs_df['date_added'] = pd.to_datetime(jobs_df['date_added'])
    
    # Calculate all required statistics
    status_counts = jobs_df['status'].value_counts()
    sentiment_counts = jobs_df['sentiment'].value_counts()
    daily_applications = jobs_df.groupby(jobs_df['date_added'].dt.date).size()
    company_counts = jobs_df['company_name'].value_counts().head(10)
    
    # Calculate metrics
    metrics = calculate_metrics(jobs_df)
    
    return {
        "status_chart": get_status_chart(status_counts),
        "sentiment_chart": get_sentiment_chart(sentiment_counts),
        "timeline_chart": get_timeline_chart(daily_applications),
        "company_chart": get_company_chart(jobs_df),
        "job_titles_chart": get_job_titles_chart(jobs_df),
        "metrics": metrics
    }

def show_metrics(metrics):
    """Display key metrics using custom styled cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    # Define the card style
    card_style = """
        <style>
        .metric-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            transition: transform 0.2s;
            margin-bottom: 20px;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .metric-title {
            color: #64748b;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .metric-value {
            color: #0f172a;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .stContainer {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
        }
        </style>
    """
    st.markdown(card_style, unsafe_allow_html=True)
    
    def create_metric_card(title, value):
        return f"""
            <div class="metric-card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
            </div>
        """
    
    with col1:
        st.markdown(create_metric_card("Total Applications", metrics["total_applications"]), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card("Weekly Average", metrics["avg_per_week"]), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card("Last 7 Days", metrics["recent_applications"]), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_metric_card("Interviewing", metrics["interview_count"]), unsafe_allow_html=True)

def show_dashboard(dashboard_data):
    """Display the dashboard with all charts and metrics."""
    if dashboard_data is None:
        st.warning("No data available for the dashboard.")
        return
    
    # Show metrics at the top
    show_metrics(dashboard_data["metrics"])
    
    # Create two columns for the first row of charts
    col1, col2 = st.columns(2)
    
    with col1:
        st_echarts(options=dashboard_data["status_chart"], height="400px", key="status_chart")
    
    with col2:
        st_echarts(options=dashboard_data["sentiment_chart"], height="400px", key="sentiment_chart")
    
    # Timeline chart in full width
    st_echarts(options=dashboard_data["timeline_chart"], height="400px", key="timeline_chart")
    
    # Job titles chart in full width
    st_echarts(options=dashboard_data["job_titles_chart"], height="400px", key="job_titles_chart")
    
    # Company chart in full width
    st_echarts(options=dashboard_data["company_chart"], height="400px", key="company_chart")

def create_applications_over_time_chart(df):
    """Create a cumulative line chart of applications over time."""
    if df.empty:
        return None
    
    # Convert date to datetime and sort
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Create a date range from April 28, 2025 to today
    start_date = pd.to_datetime('2025-04-28')
    end_date = pd.Timestamp.now()
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create a DataFrame with all dates
    all_dates = pd.DataFrame({'date': date_range})
    
    # Merge with actual data and fill missing dates with 0
    daily_counts = df.groupby('date').size().reset_index(name='count')
    merged = pd.merge(all_dates, daily_counts, on='date', how='left')
    merged['count'] = merged['count'].fillna(0)
    
    # Calculate cumulative sum
    merged['cumulative'] = merged['count'].cumsum()
    
    # Create the line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=merged['date'],
        y=merged['cumulative'],
        mode='lines',
        name='Cumulative Applications',
        line=dict(color='#1f77b4', width=3),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))
    
    # Add markers for actual application dates
    fig.add_trace(go.Scatter(
        x=daily_counts['date'],
        y=daily_counts['count'],
        mode='markers',
        name='Daily Applications',
        marker=dict(
            color='#ff7f0e',
            size=8,
            line=dict(color='white', width=1)
        )
    ))
    
    # Update layout
    fig.update_layout(
        title='Cumulative Applications Over Time',
        xaxis_title='Date',
        yaxis_title='Number of Applications',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgrey',
            zeroline=True,
            zerolinecolor='lightgrey'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgrey',
            zeroline=True,
            zerolinecolor='lightgrey'
        )
    )
    
    return fig

def show_active_applications_table(jobs_df):
    """Display a table of jobs with 'Applied' or 'Interviewing' status, ordered by applied date."""
    if jobs_df.empty:
        return

    # Filter for Applied or Interviewing status
    active_jobs = jobs_df[jobs_df['status'].isin(['Applied', 'Interviewing', 'Offered'])].copy()

    if active_jobs.empty:
        st.info("No active applications (Applied or Interviewing or Offered) to display.")
        return

    # Convert applied_date to datetime for proper sorting
    active_jobs['applied_date'] = pd.to_datetime(active_jobs['applied_date'], errors='coerce')

    # Sort by applied_date descending (most recent first)
    active_jobs = active_jobs.sort_values('applied_date', ascending=False)

    # Select and rename columns for display
    display_df = active_jobs[['company_name', 'job_title', 'status', 'applied_date', 'application_url', 'job_description']].copy()
    display_df.columns = ['Company Name', 'Job Title', 'Status', 'Applied Date', 'Application URL', 'Job Description']

    # Format the date for better display
    display_df['Applied Date'] = display_df['Applied Date'].dt.strftime('%Y-%m-%d')

    # Display the table with a header
    st.markdown("### Active Applications")
    st.markdown(f"*Showing {len(display_df)} applications with status 'Applied' or 'Interviewing'*")

    # Display the dataframe with styling
    AgGrid(
        display_df,
        use_container_width=True,
        hide_index=True
    )