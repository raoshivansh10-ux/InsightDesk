"""Multi-User Database Isolation Tests.

Verifies that users cannot access, edit, or analyze other users' datasets, 
dashboards, forecasts, anomalies, or AI endpoints.
"""
import sys
import os
import io
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.dataset import Dataset
from app.models.sales import SalesRecord

def test_isolation():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # 1. Register and Login User A
        client.post('/register', data={
            'email': 'usera@example.com',
            'business_name': 'Alpha Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'usera@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # 2. User A uploads a dataset
        csv_content = (
            "date,product,category,quantity,unit_price,region,customer_id\n"
            "2025-01-01,Widget A,Electronics,10,20.0,North,C001\n"
            "2025-01-02,Widget B,Electronics,5,50.0,North,C002\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'alpha_sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        # Logout User A
        client.get('/logout')

        # 3. Register and Login User B
        client.post('/register', data={
            'email': 'userb@example.com',
            'business_name': 'Beta Inc',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'userb@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # --- ISOLATION TESTS ---
        
        # Test A: Accessing User A's dataset details directly
        resp = client.get('/datasets/1')
        if resp.status_code == 200 and b'alpha_sales.csv' in resp.data:
            errors.append("Isolation Fail: User B can read User A's dataset detail view")
        else:
            print("[OK] Dataset detail access blocked for other users.")

        # Test B: Accessing User A's dashboard page
        resp = client.get('/dashboard/1', follow_redirects=True)
        if b'Access denied' not in resp.data:
            errors.append("Isolation Fail: User B can view User A's dashboard route")
        else:
            print("[OK] Dashboard page access blocked for other users.")

        # Test C: Accessing User A's chart API
        resp = client.get('/dashboard/api/1/charts')
        if resp.status_code != 403:
            errors.append(f"Isolation Fail: User B got status {resp.status_code} on chart API")
        else:
            print("[OK] Chart API access blocked (403).")

        # Test D: Triggering Forecast on User A's dataset
        resp = client.post('/dashboard/api/forecast/1/generate')
        if resp.status_code != 403:
            errors.append(f"Isolation Fail: User B got status {resp.status_code} on generate forecast")
        else:
            print("[OK] Generate Forecast blocked (403).")

        # Test E: Triggering RCA Scan on User A's dataset
        resp = client.post('/dashboard/api/root-cause/1/scan')
        if resp.status_code != 403:
            errors.append(f"Isolation Fail: User B got status {resp.status_code} on RCA scan")
        else:
            print("[OK] RCA scan trigger blocked (403).")

        # Test F: AI query to User A's dataset
        resp = client.post('/dashboard/api/ai/ask', json={
            'dataset_id': 1,
            'query': 'what is my total sales?'
        })
        if resp.status_code != 403:
            errors.append(f"Isolation Fail: User B got status {resp.status_code} on AI ask")
        else:
            print("[OK] AI Q&A access blocked (403).")

    if errors:
        print(f"\nFAILURES IN ISOLATION TESTS:\n" + "\n".join(errors))
        sys.exit(1)
    else:
        print("\n==================================================")
        print("DATABASE ISOLATION TESTS PASSED SUCCESSFULLY")
        print("==================================================")

if __name__ == '__main__':
    test_isolation()
