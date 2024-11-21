from flask import Flask, jsonify, request
import pandas as pd
import openai
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv('OPENAI_API_KEY', 'YPUR_API_KEY HERE')

def load_sales_data():
    try:
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'sales' in f.lower()]
        
        if not csv_files:
            print("No sales CSV file found!")
            return pd.DataFrame()
        csv_path = csv_files[0]
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip().str.lower()
        if 'date' not in df.columns:
            df['date'] = pd.date_range(start=datetime.now(), periods=len(df), freq='D')
        return df
    except Exception as e:
        print(f"Error loading CSV: {str(e)}")
        return pd.DataFrame()

def get_llm_analysis(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Analysis Error: {str(e)}")
        return "Unable to generate AI analysis at this time."

@app.route('/api/team_performance', methods=['GET'])
def team_performance():
    # Overall team performance
    df = load_sales_data()
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
def performance_trends():
    # Performance trends
    time_period = request.args.get('time_period', 'monthly')
    
    df = load_sales_data()
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

@app.route('/api/rep_performance', methods=['GET'])
def rep_performance():
    rep_id = request.args.get('rep_id')
    if not rep_id:
        return jsonify({"error": "Rep ID is required"}), 400

    df = load_sales_data()
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)