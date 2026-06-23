"""Test for AI Module (Phase 8)."""
import sys
import os
import io
import json
from datetime import datetime, timedelta

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.dataset import Dataset
from app.models.insight import Insight
from app.models.anomaly import Anomaly
from app.models.root_cause import RootCauseReport
from app.ai.engine import generate_recommendations, answer_nlq

def test_phase8():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # Setup a user
        client.post('/register', data={
            'email': 'ai@example.com',
            'business_name': 'AI Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'ai@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # Upload minimal data
        csv_content = "date,product,category,quantity,unit_price,region,customer_id\n"
        csv_content += "2025-01-01,Widget A,Electronics,10,10.0,North,C001\n"
        
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'ai_sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        with app.app_context():
            dataset_id = 1
            
            # Create a mock Anomaly and RCA so the AI engine has context
            anomaly = Anomaly(
                dataset_id=dataset_id,
                detected_at=datetime(2025, 1, 1),
                metric='revenue',
                method='z-score',
                observed_value=50.0,
                expected_range_low=90.0,
                expected_range_high=110.0,
                severity='high',
                message='Revenue dropped',
                type='negative'
            )
            db.session.add(anomaly)
            db.session.commit()
            
            rca = RootCauseReport(
                dataset_id=dataset_id,
                anomaly_id=anomaly.id,
                period_baseline='2024-12-01 to 2024-12-31',
                period_current='2025-01-01',
                metric='revenue',
                total_delta_pct=-50.0,
                contributors_json={"negative": [{"factor": "Product", "value": "Widget B", "impact": -50.0}]}
            )
            db.session.add(rca)
            db.session.commit()
            
            # Test 1: Generate Recommendations
            # This should either return the fallback (if no key) or actual JSON from Gemini
            recs = generate_recommendations(dataset_id)
            if not recs or len(recs) != 3:
                errors.append(f"generate_recommendations did not return 3 items. Got: {recs}")
            else:
                print(f"[OK] Recommendations generated: {len(recs)} items")
                print(f"      Example: {recs[0].get('title')}")
                
            # Verify DB persistence if it was Gemini
            has_key = os.getenv('GEMINI_API_KEY') is not None
            if has_key:
                insight = Insight.query.filter_by(insight_type='recommendation').first()
                if not insight:
                    errors.append("Recommendation insight not saved to DB!")
                else:
                    print("[OK] Recommendation saved to DB.")
            else:
                print("[INFO] Running in offline fallback mode (no DB save for fallback).")

            # Test 2: NLQ Engine directly
            answer = answer_nlq(dataset_id, "Why did revenue drop?")
            if not answer:
                errors.append("answer_nlq returned empty response!")
            else:
                print(f"[OK] NLQ Answer generated.")
                print(f"      {answer[:100]}...")

        # Test 3: NLQ API Endpoint
        resp = client.post('/dashboard/api/ai/ask', json={
            'dataset_id': 1,
            'query': 'What should I do?'
        })
        assert resp.status_code == 200, f"API failed: {resp.status_code}"
        
        data = json.loads(resp.data)
        if not data.get('answer'):
            errors.append("API response missing 'answer' field.")
        else:
            print("[OK] API successfully processed NLQ request.")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 8 -- ALL CHECKS PASSED")
        print(f"{'='*50}")

if __name__ == '__main__':
    test_phase8()
