"""Test for Automated Root Cause Analysis (Phase 5)."""
import sys
import os
import io
import json

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.anomaly import Anomaly
from app.models.root_cause import RootCauseReport
from app.root_cause.engine import analyze_root_cause

def test_phase5():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # Setup a user
        client.post('/auth/register', data={
            'email': 'rca@example.com',
            'business_name': 'RCA Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/auth/login', data={
            'email': 'rca@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # Upload dataset with a few normal days, and one massive spike driven by a specific region/product
        csv_content = (
            "date,product,category,quantity,unit_price,region,customer_id\n"
            "2025-01-01,Widget A,Electronics,10,10.0,North,C001\n"
            "2025-01-02,Widget A,Electronics,12,10.0,North,C001\n"
            "2025-01-03,Widget B,Electronics,5,20.0,South,C002\n"
            "2025-01-04,Widget A,Electronics,10,10.0,North,C001\n"
            # Spike day
            "2025-01-05,Widget B,Electronics,500,20.0,South,C002\n" 
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'rca_sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        # Trigger anomaly detection (this usually happens on dashboard load or via background task)
        from app.analytics.anomaly_detector import detect_anomalies
        with app.app_context():
            detect_anomalies(1)
            
        # Test 1: Check Anomaly was saved to DB
        with app.app_context():
            anomalies = Anomaly.query.filter_by(dataset_id=1).all()
            if not anomalies:
                errors.append("No anomalies persisted to DB!")
            else:
                spike = next((a for a in anomalies if a.dimension_value == '2025-01-05'), None)
                if not spike:
                    errors.append("Spike anomaly on 2025-01-05 not found in DB!")
                else:
                    print(f"[OK] Anomaly persisted to DB: ID {spike.id}, Severity: {spike.severity}")

        # Test 2: Trigger RCA Scan via API
        resp = client.post('/dashboard/api/root-cause/1/scan')
        assert resp.status_code == 200, f"RCA Scan failed: {resp.status_code} {resp.data}"
        scan_data = json.loads(resp.data)
        
        if scan_data['triggered'] == 0:
            print("[INFO] RCA scan did not trigger any reports (likely due to low severity).")
        else:
            print(f"[OK] RCA scan triggered {scan_data['triggered']} reports")

        # Test 3: Fetch RCA via API and verify contributors
        with app.app_context():
            anomaly_id = Anomaly.query.filter_by(dataset_id=1, dimension_value='2025-01-05').first().id
            
        resp = client.get(f'/dashboard/api/root-cause/1/{anomaly_id}')
        assert resp.status_code == 200, f"Fetch RCA failed: {resp.status_code} {resp.data}"
        rca_data = json.loads(resp.data)
        
        contributors = rca_data['contributors']
        
        # We expect South region to be a top positive contributor
        south_contrib = next((c for c in contributors if c.get('dimension') == 'region' and c.get('dimension_value') == 'South'), None)
        if not south_contrib or south_contrib['delta_value'] <= 0:
            errors.append(f"South region not found as positive contributor! Contributors: {contributors}")
        else:
            print(f"[OK] South region correctly identified as contributor ({south_contrib['contribution_pct']}%)")
            
        # We expect Widget B to be a top positive contributor
        widget_b_contrib = next((c for c in contributors if c.get('dimension') == 'product' and c.get('dimension_value') == 'Widget B'), None)
        if not widget_b_contrib or widget_b_contrib['delta_value'] <= 0:
            errors.append("Widget B not found as positive contributor!")
        else:
            print(f"[OK] Widget B correctly identified as contributor ({widget_b_contrib['contribution_pct']}%)")

        # Test 4: Check Stockout Heuristic
        # Widget A sold consistently then 0 on 01-05
        stockout_signal = next((c for c in contributors if c.get('type') == 'possible_stockout'), None)
        if not stockout_signal or stockout_signal['dimension_value'] != 'Widget A':
            errors.append(f"Widget A stockout signal not detected! Found: {stockout_signal}")
        else:
            print(f"[OK] Stockout heuristic correctly flagged Widget A")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 5 -- ALL CHECKS PASSED")
        print(f"{'='*50}")

if __name__ == '__main__':
    test_phase5()
