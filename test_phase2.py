"""Quick smoke test for Phase 2 -- Dashboard + Analytics."""
import sys
import os
import io
import json

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.dataset import Dataset
from app.models.sales import SalesRecord


def test_phase2():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # Setup a user and dataset
        client.post('/register', data={
            'email': 'dashboard@example.com',
            'business_name': 'Dash Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'dashboard@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # Upload dataset
        csv_content = (
            "date,product,category,quantity,unit_price,region,customer_id\n"
            "2025-01-15,Widget A,Electronics,10,29.99,North,C001\n"
            "2025-01-16,Widget B,Home,5,49.99,South,C002\n"
            "2025-01-17,Widget A,Electronics,8,29.99,North,C001\n"
            "2025-02-01,Widget C,Electronics,3,99.99,East,C003\n"
            "2025-02-05,Widget B,Home,12,49.99,West,C004\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data,
                    content_type='multipart/form-data', follow_redirects=True)
        
        # Test 1: Dashboard redirect from /dashboard/
        resp = client.get('/dashboard/')
        assert resp.status_code == 302
        assert '/dashboard/1' in resp.headers.get('Location')
        print("[OK] GET /dashboard/ -> redirects to latest dataset")

        # Test 2: Load Dashboard for dataset 1
        resp = client.get('/dashboard/1')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Command Center' in html
        assert '$1,689.62' in html  # Total revenue
        assert 'Widget B' in html # Top product is Widget B ((5+12)*49.99 = 849.83)
        assert '5' in html # 5 orders
        print("[OK] GET /dashboard/1 -> 200, KPIs computed correctly")

        # Test 3: API endpoint for charts
        resp = client.get('/dashboard/api/1/charts')
        assert resp.status_code == 200
        chart_data = json.loads(resp.data)
        assert 'trend' in chart_data
        assert 'category' in chart_data
        assert len(chart_data['trend']['labels']) > 0
        assert len(chart_data['category']['labels']) > 0
        print("[OK] GET /dashboard/api/1/charts -> 200, returns JSON chart data")

        # Test 4: Cross-account isolation for dashboard
        client.get('/logout')
        client.post('/register', data={
            'email': 'other2@example.com',
            'business_name': 'Other2 Inc',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        client.post('/login', data={
            'email': 'other2@example.com',
            'password': 'password123',
        }, follow_redirects=True)
        
        resp = client.get('/dashboard/1', follow_redirects=True)
        assert 'Access denied' in resp.data.decode('utf-8')
        print("[OK] Dashboard isolation: other user cannot view dashboard 1")

        resp = client.get('/dashboard/api/1/charts')
        assert resp.status_code == 403
        print("[OK] API isolation: other user cannot fetch chart data 1")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 2 -- ALL CHECKS PASSED")
        print(f"{'='*50}")


if __name__ == '__main__':
    test_phase2()
