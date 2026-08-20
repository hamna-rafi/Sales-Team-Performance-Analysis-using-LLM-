# Sales-Team-Performance-Analysis-using-LLM

An LLM-based backend system that analyzes sales data and provides actionable insights for both individual sales reps and the overall team.

## Features

- Individual sales rep performance evaluation
- Overall team performance assessment
- Sales trends analysis and forecasting (monthly/quarterly)
- Side-by-side rep comparison
- Data export in multiple formats (JSON, CSV, summary)
- LLM-powered insights and coaching recommendations
- In-memory caching for improved performance
- Rate limiting to prevent API abuse
- RESTful API with structured error responses

## Tech Stack

- **Flask**: Lightweight web framework for building APIs
- **Pandas**: Data manipulation and analysis
- **OpenAI GPT-4**: LLM for generating insights and recommendations
- **Flask-CORS**: Cross-origin resource sharing support

## Setup Instructions

1. Create and activate virtual environment:
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

2. Install the dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

4. Run the app:
```bash
python app.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check and system status |
| `/api/team_performance` | GET | Overall team performance metrics + AI analysis |
| `/api/performance_trends` | GET | Performance trends over time |
| `/api/rep_performance` | GET | Individual rep performance + coaching insights |
| `/api/compare_reps` | GET | Side-by-side rep comparison |
| `/api/export` | GET | Export data in different formats |

### Example Requests

```bash
# Health check
curl http://127.0.0.1:5000/api/health

# Team performance
curl http://127.0.0.1:5000/api/team_performance

# Quarterly trends
curl http://127.0.0.1:5000/api/performance_trends?time_period=quarterly

# Individual performance
curl http://127.0.0.1:5000/api/rep_performance?rep_id=183

# Compare two reps
curl http://127.0.0.1:5000/api/compare_reps?rep_ids=183,184

# Export as CSV
curl http://127.0.0.1:5000/api/export?format=csv
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Your OpenAI API key (required) |
| `LLM_MODEL` | `gpt-4` | OpenAI model to use |
| `PORT` | `5000` | Server port |
| `FLASK_DEBUG` | `true` | Enable debug mode |
