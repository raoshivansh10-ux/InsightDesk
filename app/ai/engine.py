import os
import json
import google.generativeai as genai
from app.extensions import db
from app.models.dataset import Dataset
from app.models.root_cause import RootCauseReport
from app.models.forecast import Forecast
from app.models.insight import Insight

# Configure Gemini
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """You are the AI engine for InsightDesk, a business intelligence platform.
Your task is to act as an expert data analyst synthesizing hard data into clear, actionable business advice.
STRICT RULES:
1. Do NOT invent external context (e.g., inflation, macroeconomics, weather).
2. Base your answers strictly on the provided data from the Root Cause Engine and Forecasting Engine.
3. Be concise and professional.
"""

def generate_recommendations(dataset_id):
    """
    Generates a 3-bullet action plan based on the latest Root Cause and Forecast.
    """
    if not api_key:
        return _fallback_recommendations()

    dataset = Dataset.query.get(dataset_id)
    if not dataset:
        return None

    # Fetch latest RCA and Forecast
    rca = RootCauseReport.query.filter_by(dataset_id=dataset_id).order_by(RootCauseReport.generated_at.desc()).first()
    forecast = Forecast.query.filter_by(dataset_id=dataset_id).order_by(Forecast.generated_at.desc()).first()

    if not rca:
        return _fallback_no_data()

    # Construct the data payload for the prompt
    data_context = f"Industry: {dataset.industry_type}\n"
    data_context += f"Recent Anomaly: {rca.anomaly.date}, metric '{rca.metric}' changed by {rca.total_delta_pct}%\n"
    data_context += f"Root Cause Contributors: {json.dumps(rca.contributors_json)}\n"
    
    if forecast:
        data_context += f"Forecast Outlook (Next 30 days): {forecast.outlook_score:.2f}% expected growth.\n"

    prompt = f"""
{SYSTEM_PROMPT}

[DATA]
{data_context}

[TASK]
Based on the data above, synthesize a 3-bullet actionable recommendation plan.
Focus particularly on addressing any inferred stockouts, churn risks, or major negative contributors. 
If the anomaly was a positive spike, recommend ways to capitalize on the winning segments.

[OUTPUT FORMAT]
Return a pure JSON array containing exactly 3 objects. Do not wrap in markdown blocks like ```json.
Each object must have:
- "title": A short boldable title
- "description": The specific action item details
"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        content = json.loads(response.text)
        
        # Save to DB
        insight = Insight(
            dataset_id=dataset_id,
            insight_type='recommendation',
            content_json=content
        )
        db.session.add(insight)
        db.session.commit()
        
        return content

    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return _fallback_error()

def answer_nlq(dataset_id, query):
    """
    Answers a natural language question using the dataset context.
    """
    if not api_key:
        return "I'm currently running in offline mode because the GEMINI_API_KEY is not configured in the `.env` file. Please add it to enable Natural Language Queries!"

    dataset = Dataset.query.get(dataset_id)
    if not dataset:
        return "Dataset not found."

    rca = RootCauseReport.query.filter_by(dataset_id=dataset_id).order_by(RootCauseReport.generated_at.desc()).first()
    forecast = Forecast.query.filter_by(dataset_id=dataset_id).order_by(Forecast.generated_at.desc()).first()
    
    # We could also fetch KPIs here, but for now RCA and Forecast are the heavy lifters
    data_context = f"Industry: {dataset.industry_type}\n"
    if rca:
        data_context += f"Latest Root Cause Report (for anomaly on {rca.anomaly.date}): {json.dumps(rca.contributors_json)}\n"
    if forecast:
        data_context += f"30-day Forecast Outlook Score: {forecast.outlook_score:.2f}%\n"

    prompt = f"""
{SYSTEM_PROMPT}

[AVAILABLE DATA CONTEXT]
{data_context}

[USER QUESTION]
{query}

[TASK]
Answer the user's question directly and concisely using only the data provided above. 
If the answer cannot be determined from the provided data, politely say so.
"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Save to DB for history
        insight = Insight(
            dataset_id=dataset_id,
            insight_type='nlq_answer',
            content_json={'query': query, 'answer': response.text}
        )
        db.session.add(insight)
        db.session.commit()
        
        return response.text
    except Exception as e:
        print(f"Error answering NLQ: {e}")
        return "I encountered an error trying to process your request."

# --- Fallbacks ---

def _fallback_recommendations():
    return [
        {
            "title": "API Key Required",
            "description": "Please add a GEMINI_API_KEY to your .env file to unlock AI-generated recommendations."
        },
        {
            "title": "Monitor Top Regions",
            "description": "Review the Root Cause Insights panel to see which regions are over-indexing."
        },
        {
            "title": "Forecast Outlook",
            "description": "Check the Revenue Trend chart's dashed line to prepare for the upcoming 30-day volume."
        }
    ]

def _fallback_no_data():
    return [
        {
            "title": "Waiting for Alerts",
            "description": "Actionable recommendations will appear here automatically once an anomaly is detected."
        }
    ]

def _fallback_error():
    return [
        {
            "title": "AI Engine Error",
            "description": "The AI engine encountered a temporary error generating recommendations."
        }
    ]
