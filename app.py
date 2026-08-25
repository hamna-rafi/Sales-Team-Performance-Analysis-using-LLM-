from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import openai
from datetime import datetime
import os
import logging
import time
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv('OPENAI_API_KEY', 'YPUR_API_KEY HERE')

_sales_data_cache = None
_cache_timestamp = 0
CACHE_TTL = 300

def get_cached_sales_data():
    global _sales_data_cache, _cache_timestamp
    current_time = time.time()
    if _sales_data_cache is not None and (current_time - _cache_timestamp) < CACHE_TTL:
        logger.info("Returning cached sales data")
        return _sales_data_cache
    _sales_data_cache = load_sales_data()
    _cache_timestamp = current_time
    return _sales_data_cache

def rate_limit(max_calls=10, period=60):
    calls = []
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if now - c < period]
            if len(calls) >= max_calls:
                return jsonify({"error": "Rate limit exceeded. Try again later."}), 429
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def load_sales_data():
    try:
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'sales' in f.lower()]
        
        if not csv_files:
            logger.warning("No sales CSV file found!")
            return pd.DataFrame()
        csv_path = csv_files[0]
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip().str.lower()
        if 'date' not in df.columns:
            df['date'] = pd.date_range(start=datetime.now(), periods=len(df), freq='D')
        logger.info(f"Loaded {len(df)} rows from {csv_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading CSV: {str(e)}")
        return pd.DataFrame()

def get_llm_analysis(prompt, temperature=0.7, max_tokens=2000):
    try:
        response = openai.chat.completions.create(
            model=os.getenv('LLM_MODEL', 'gpt-4'),
            messages=[
                {"role": "system", "content": "You are an expert sales analyst. Provide concise, actionable insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        logger.info(f"LLM analysis completed, tokens used: {response.usage.total_tokens}")
        return response.choices[0].message.content
    except openai.RateLimitError:
        logger.warning("OpenAI rate limit hit")
        return "Analysis temporarily unavailable due to rate limiting. Please retry in a moment."
    except openai.AuthenticationError:
        logger.error("Invalid OpenAI API key")
        return "Analysis unavailable: authentication error."
    except Exception as e:
        logger.error(f"LLM Analysis Error: {str(e)}")
        return "Unable to generate AI analysis at this time."

@app.route('/api/health', methods=['GET'])
def health_check():
    df = get_cached_sales_data()
    return jsonify({
        "status": "healthy",
        "data_loaded": not df.empty,
        "row_count": len(df),
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0"
    })

@app.route('/api/team_performance', methods=['GET'])
@rate_limit(max_calls=20, period=60)
def team_performance():
    df = get_cached_sales_data()
    if df.empty:
        return jsonify({"error": "Failed to load sales data"}), 500

    try:
        metrics = {
            "total_confirmed_revenue": float(df['revenue_confirmed'].sum()),
            "total_pending_revenue": float(df['revenue_pending'].sum()),
            "total_estimated_revenue": float(df['estimated_revenue'].sum()),
            "average_deal_value": float(df['avg_deal_value_30_days'].mean()),
            "average_close_rate": float(df['avg_close_rate_30_days'].mean()),
            "total_tours_booked": int(df['tours_booked'].sum()),
            "total_applications": int(df['applications'].sum()),
            "average_tours_per_lead": float(df['tours_per_lead'].mean()),
            "average_apps_per_tour": float(df['apps_per_tour'].mean()),
            "tours_in_pipeline": int(df['tours_in_pipeline'].sum()),
            "total_employees": df['employee_id'].nunique()
        }

        top_performers = (
            df.groupby(['employee_id', 'employee_name'])['revenue_confirmed']
            .sum()
            .sort_values(ascending=False)
            .head(3)
            .reset_index()
            .to_dict('records')
        )

        activity_metrics = {
            "tours_scheduled": int(df['tours_scheduled'].sum()),
            "tours_pending": int(df['tours_pending'].sum()),
            "tours_cancelled": int(df['tours_cancelled'].sum()),
            "daily_calls": {
                "Monday": int(df.get('mon_call', 0).sum()),
                "Tuesday": int(df.get('tue_call', 0).sum()),
                "Wednesday": int(df.get('wed_call', 0).sum()),
                "Thursday": int(df.get('thur_call', 0).sum()),
                "Friday": int(df.get('fri_call', 0).sum()),
                "Saturday": int(df.get('sat_call', 0).sum()),
                "Sunday": int(df.get('sun_call', 0).sum())
            }
        }

        prompt = f"""
        Analyze the following team performance metrics:
        
        Revenue Metrics:
        - Total Confirmed Revenue: ${metrics['total_confirmed_revenue']:,.2f}
        - Total Pending Revenue: ${metrics['total_pending_revenue']:,.2f}
        - Average Deal Value (30 days): ${metrics['average_deal_value']:,.2f}
        - Average Close Rate (30 days): {metrics['average_close_rate']:.1%}
        
        Tour and Application Metrics:
        - Total Tours Booked: {metrics['total_tours_booked']}
        - Total Applications: {metrics['total_applications']}
        - Average Tours per Lead: {metrics['average_tours_per_lead']:.2f}
        - Average Applications per Tour: {metrics['average_apps_per_tour']:.2f}
        - Tours in Pipeline: {metrics['tours_in_pipeline']}
        
        Team Size: {metrics['total_employees']} employees
        
        Top Performers:
        {top_performers}
        
        Daily Activity:
        - Tours Scheduled: {activity_metrics['tours_scheduled']}
        - Tours Pending: {activity_metrics['tours_pending']}
        - Tours Cancelled: {activity_metrics['tours_cancelled']}
        
        Please provide:
        1. Overall team performance assessment
        2. Analysis of conversion metrics (tours to applications)
        3. Activity level analysis and recommendations
        4. Strategic recommendations for improvement
        """

        analysis = get_llm_analysis(prompt)
        return jsonify({
            "metrics": metrics,
            "top_performers": top_performers,
            "activity_metrics": activity_metrics,
            "analysis": analysis
        })
    
    except Exception as e:
        return jsonify({"error": f"Internal processing error: {str(e)}"}), 500

@app.route('/api/performance_trends', methods=['GET'])
@rate_limit(max_calls=20, period=60)
def performance_trends():
    time_period = request.args.get('time_period', 'monthly')
    
    df = get_cached_sales_data()
    if df.empty:
        return jsonify({"error": "Failed to load sales data"}), 500

    try:
        df['date'] = pd.to_datetime(df['date'])
        if time_period == 'monthly':
            grouped_data = df.groupby(pd.Grouper(key='date', freq='M')).agg({
                'revenue_confirmed': 'sum',
                'tours_booked': 'sum',
                'applications': 'sum',
                'avg_close_rate_30_days': 'mean'
            }).reset_index()
        elif time_period == 'quarterly':
            grouped_data = df.groupby(pd.Grouper(key='date', freq='Q')).agg({
                'revenue_confirmed': 'sum',
                'tours_booked': 'sum',
                'applications': 'sum',
                'avg_close_rate_30_days': 'mean'
            }).reset_index()
        else:
            return jsonify({"error": "Invalid time period. Use 'monthly' or 'quarterly'"}), 400
        prompt = f"""
        Analyze sales performance trends:
        
        Trends Overview:
        - Time Period: {time_period}
        - Total Periods Analyzed: {len(grouped_data)}
        - Revenue Range: ${grouped_data['revenue_confirmed'].min():,.2f} - ${grouped_data['revenue_confirmed'].max():,.2f}
        - Average Tours Booked: {grouped_data['tours_booked'].mean():.2f}
        - Average Applications: {grouped_data['applications'].mean():.2f}

        Please provide:
        1. Performance trend analysis
        2. Predictive insights
        3. Recommendations for maintaining/improving trajectory
        """

        analysis = get_llm_analysis(prompt)

        return jsonify({
            "trends": grouped_data.to_dict(orient='records'),
            "analysis": analysis
        })
    
    except Exception as e:
        return jsonify({"error": f"Trend analysis error: {str(e)}"}), 500

@app.route('/api/compare_reps', methods=['GET'])
@rate_limit(max_calls=15, period=60)
def compare_reps():
    rep_ids = request.args.get('rep_ids', '')
    if not rep_ids:
        return jsonify({"error": "Provide comma-separated rep_ids parameter"}), 400

    ids = [id.strip() for id in rep_ids.split(',')]
    if len(ids) < 2:
        return jsonify({"error": "At least 2 rep IDs required for comparison"}), 400

    df = get_cached_sales_data()
    if df.empty:
        return jsonify({"error": "Failed to load sales data"}), 500

    try:
        comparisons = []
        for rid in ids:
            rep_data = df[df['employee_id'].astype(str) == str(rid)]
            if rep_data.empty:
                continue
            comparisons.append({
                "employee_id": rid,
                "employee_name": rep_data['employee_name'].iloc[0],
                "revenue_confirmed": float(rep_data['revenue_confirmed'].sum()),
                "close_rate": float(rep_data['avg_close_rate_30_days'].mean()),
                "tours_booked": int(rep_data['tours_booked'].sum()),
                "applications": int(rep_data['applications'].sum()),
                "avg_deal_value": float(rep_data['avg_deal_value_30_days'].mean()),
            })

        if len(comparisons) < 2:
            return jsonify({"error": "Not enough valid reps found for comparison"}), 404

        prompt = f"""
        Compare the following sales representatives:
        
        {comparisons}
        
        Please provide:
        1. Side-by-side performance comparison
        2. Each rep's relative strengths and weaknesses
        3. Who is performing best overall and why
        4. Specific coaching suggestions for each rep
        """

        analysis = get_llm_analysis(prompt)
        return jsonify({
            "comparisons": comparisons,
            "analysis": analysis
        })
    except Exception as e:
        logger.error(f"Comparison error: {str(e)}")
        return jsonify({"error": f"Comparison error: {str(e)}"}), 500

@app.route('/api/rep_performance', methods=['GET'])
@rate_limit(max_calls=20, period=60)
def rep_performance():
    rep_id = request.args.get('rep_id')
    if not rep_id:
        return jsonify({"error": "Rep ID is required"}), 400

    df = get_cached_sales_data()
    if df.empty:
        return jsonify({"error": "Failed to load sales data"}), 500

    try:
        rep_data = df[df['employee_id'].astype(str) == str(rep_id)]
        if rep_data.empty:
            return jsonify({"error": "No data found for this representative"}), 404
        metrics = {
            "employee_id": rep_id,
            "employee_name": rep_data['employee_name'].iloc[0],
            "total_confirmed_revenue": float(rep_data['revenue_confirmed'].sum()),
            "total_pending_revenue": float(rep_data['revenue_pending'].sum()),
            "total_estimated_revenue": float(rep_data.get('estimated_revenue', 0).sum()),
            "average_deal_value": float(rep_data['avg_deal_value_30_days'].mean()),
            "close_rate": float(rep_data['avg_close_rate_30_days'].mean()),
            "total_tours_booked": int(rep_data['tours_booked'].sum()),
            "total_applications": int(rep_data['applications'].sum()),
            "tours_per_lead": float(rep_data['tours_per_lead'].mean()),
            "apps_per_tour": float(rep_data['apps_per_tour'].mean()),
            "tours_in_pipeline": int(rep_data['tours_in_pipeline'].sum()),
            "tours_scheduled": int(rep_data['tours_scheduled'].sum()),
            "tours_pending": int(rep_data['tours_pending'].sum()),
            "tours_cancelled": int(rep_data['tours_cancelled'].sum())
        }
        daily_activity = {
            "Calls": {
                "Monday": int(rep_data['mon_call'].sum()),
                "Tuesday": int(rep_data['tue_call'].sum()),
                "Wednesday": int(rep_data['wed_call'].sum()),
                "Thursday": int(rep_data['thur_call'].sum()),
                "Friday": int(rep_data['fri_call'].sum()),
                "Saturday": int(rep_data['sat_call'].sum()),
                "Sunday": int(rep_data['sun_call'].sum())
            },
            "Daily Text Interactions": {
                "Monday": rep_data['mon_text'].tolist(),
                "Tuesday": rep_data['tue_text'].tolist(),
                "Wednesday": rep_data['wed_text'].tolist(),
                "Thursday": rep_data['thur_text'].tolist(),
                "Friday": rep_data['fri_text'].tolist(),
                "Saturday": rep_data['sat_text'].tolist(),
                "Sunday": rep_data['sun_text'].tolist()
            }
        }

        prompt = f"""
        Analyze the performance of sales representative {rep_id}:
        
        Performance Metrics:
        - Total Confirmed Revenue: ${metrics['total_confirmed_revenue']:,.2f}
        - Total Pending Revenue: ${metrics['total_pending_revenue']:,.2f}
        - Estimated Revenue: ${metrics['total_estimated_revenue']:,.2f}
        - Average Deal Value: ${metrics['average_deal_value']:,.2f}
        - Close Rate: {metrics['close_rate']:.1%}
        - Total Tours Booked: {metrics['total_tours_booked']}
        - Total Applications: {metrics['total_applications']}
        - Tours per Lead: {metrics['tours_per_lead']:.2f}
        - Applications per Tour: {metrics['apps_per_tour']:.2f}
        - Tours in Pipeline: {metrics['tours_in_pipeline']}
        
        Activity Overview:
        - Tours Scheduled: {metrics['tours_scheduled']}
        - Tours Pending: {metrics['tours_pending']}
        - Tours Cancelled: {metrics['tours_cancelled']}

        Daily Calls Breakdown:
        {daily_activity['Calls']}

        Please provide:
        1. Detailed performance assessment
        2. Strengths and areas for improvement
        3. Personalized coaching recommendations
        4. Insights from daily activity patterns
        """
        
        analysis = get_llm_analysis(prompt)

        return jsonify({
            "metrics": metrics,
            "daily_activity": daily_activity,
            "analysis": analysis
        })
    
    except Exception as e:
        return jsonify({"error": f"Representative analysis error: {str(e)}"}), 500

@app.route('/api/export', methods=['GET'])
def export_data():
    format_type = request.args.get('format', 'json')
    df = get_cached_sales_data()
    if df.empty:
        return jsonify({"error": "No data available"}), 500

    if format_type == 'json':
        return jsonify(df.to_dict(orient='records'))
    elif format_type == 'csv':
        csv_data = df.to_csv(index=False)
        return csv_data, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=sales_export.csv'}
    elif format_type == 'summary':
        summary = {
            "total_rows": len(df),
            "columns": list(df.columns),
            "date_range": {
                "start": str(df['date'].min()) if 'date' in df.columns else None,
                "end": str(df['date'].max()) if 'date' in df.columns else None
            },
            "total_revenue": float(df['revenue_confirmed'].sum()),
            "unique_employees": int(df['employee_id'].nunique())
        }
        return jsonify(summary)
    else:
        return jsonify({"error": "Unsupported format. Use 'json', 'csv', or 'summary'"}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "available_endpoints": [
        "/api/health",
        "/api/team_performance",
        "/api/performance_trends?time_period=monthly|quarterly",
        "/api/rep_performance?rep_id=<id>",
        "/api/compare_reps?rep_ids=<id1>,<id2>",
        "/api/export?format=json|csv|summary"
    ]}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    logger.info(f"Starting Sales Performance API on port {port}")
    app.run(debug=debug, host='0.0.0.0', port=port)