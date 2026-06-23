"""Test for Anomaly Detection (Phase 3)."""
import sys
import os
import io

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.analytics.anomaly_detector import detect_anomalies
from app.models.dataset import Dataset


def test_phase3():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # Setup a user
        client.post('/register', data={
            'email': 'anomaly@example.com',
            'business_name': 'Anomaly Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'anomaly@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # Upload dataset with 5 normal days and 1 massive outlier day
        csv_content = (
            "date,product,category,quantity,unit_price,region,customer_id\n"
            "2025-01-01,Widget A,Electronics,10,10.0,North,C001\n" # 100
            "2025-01-02,Widget A,Electronics,12,10.0,North,C001\n" # 120
            "2025-01-03,Widget A,Electronics,9,10.0,North,C001\n"  # 90
            "2025-01-04,Widget A,Electronics,11,10.0,North,C001\n" # 110
            "2025-01-05,Widget A,Electronics,10,10.0,North,C001\n" # 100
            "2025-01-06,Widget A,Electronics,500,10.0,North,C002\n" # 5000 (MASSIVE SPIKE)
            "2025-01-07,Widget A,Electronics,10,10.0,North,C001\n" # 100
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'anomaly_sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data,
                    content_type='multipart/form-data', follow_redirects=True)
        
        # Test 1: Fetch anomalies directly via python API
        # Dataset id is 1 because testing db is fresh
        anomalies = detect_anomalies(1)
        
        # We expect exactly 1 anomaly on '2025-01-06'
        anomaly_dates = [a['date'] for a in anomalies]
        assert '2025-01-06' in anomaly_dates, f"Anomaly not detected! Found: {anomalies}"
        print("[OK] Outlier successfully detected on 2025-01-06")

        spike = next(a for a in anomalies if a['date'] == '2025-01-06')
        assert spike['type'] == 'positive'
        assert spike['actual_value'] == 5000.0
        print(f"[OK] Anomaly details are correct (Severity: {spike['severity']}, Diff: {spike['diff_pct']:.1f}%)")

        # Test 2: Check Dashboard UI rendering
        resp = client.get('/dashboard/1')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Alerts &amp; Anomalies' in html or 'Alerts & Anomalies' in html
        assert '2025-01-06' in html
        assert '5,000.00' in html
        assert 'Spiked' in html
        print("[OK] Anomalies successfully rendered in the Dashboard UI")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 3 -- ALL CHECKS PASSED")
        print(f"{'='*50}")


if __name__ == '__main__':
    test_phase3()
