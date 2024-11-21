# Sales-Team-Performance-Analysis-using-LLM-
An LLM-based backend system that can analyze sales data and provide insights for both individual sales reps and team members.

Features:
An evaluation of how individual sales reps are performing in their roles as a consultant.
Overall team performance assessment
Sales trends analysis and forecasting
LLM-powered insights and recommendations
RESTful API endpoints

Stack used:
FastAPI: Modern, fast web framework for building APIs
Pandas: Data manipulation and analysis
OpenAI GPT-4: LLM for generating insights

Setup Instructions:
Create virtual environment: 
python -m venv venv
venv\Scripts\activate

Install the dependencies:
pip install -r requirements.txt

Run app:
python app.py

API testing through insomnia/postman:
Team performance: http://127.0.0.1:5000/api/team_performance
Performance Trends: http://127.0.0.1:5000/api/performance_trends?time_period=quarterly
Individual performance: http://127.0.0.1:5000/api/rep_performance?rep_id=183
