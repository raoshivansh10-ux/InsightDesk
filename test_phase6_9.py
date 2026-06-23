"""Test for Phase 6 & 9 (Reporting Engine)."""

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
from app.models.report_subscription import ReportSubscription

def test_phase6_9():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # Setup a user
        client.post('/register', data={
            'email': 'report@example.com',
            'business_name': 'Report Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'report@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # Upload minimal data
        csv_content = "date,product,category,quantity,unit_price,region,customer_id\n"
        csv_content += "2025-01-01,Widget A,Electronics,10,10.0,North,C001\n"
        
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'report_sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        # Test API Endpoint to Subscribe
        resp = client.post('/dashboard/api/reports/subscribe', json={'dataset_id': 1})
        if resp.status_code != 200:
            errors.append(f"Failed to subscribe: {resp.status_code}")
        
        with app.app_context():
            # Check DB
            sub = ReportSubscription.query.filter_by(dataset_id=1).first()
            if not sub or not sub.is_active:
                errors.append("Subscription not saved in DB correctly.")
            else:
                print("[OK] Subscription saved in DB.")

            # Create some mock data for the email
            anomaly = Anomaly(
                dataset_id=1,
                detected_at=datetime.utcnow(),
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
            
            insight = Insight(
                dataset_id=1,
                insight_type='recommendation',
                content_json={'recommendations': [{'title': 'Test Rec', 'description': 'Test Desc', 'impact_estimate': 'High'}]}
            )
            db.session.add(insight)
            db.session.commit()

        # Test "Send Now" endpoint (will hit our dev-mode console fallback)
        print("\n--- TRIGGERING REPORT ---")
        resp = client.post('/dashboard/api/reports/send-now', json={'dataset_id': 1})
        if resp.status_code != 200:
            errors.append(f"Failed to send report: {resp.status_code}")
        else:
            print("[OK] Report generation and dispatch API succeeded.")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 6 & 9 -- ALL CHECKS PASSED")
        print(f"{'='*50}")

if __name__ == '__main__':
    test_phase6_9()
