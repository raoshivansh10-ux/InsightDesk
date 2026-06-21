"""Quick smoke test for Phase 1 -- Auth + Upload + DB."""
import sys
import os
import io

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.dataset import Dataset
from app.models.sales import SalesRecord
from app.models.customer import Customer


def test_phase1():
    app = create_app('testing')
    errors = []

    with app.app_context():
        # 1. Tables created
        tables = db.engine.table_names() if hasattr(db.engine, 'table_names') else \
                 [t for t in db.inspect(db.engine).get_table_names()]
        print(f"[✓] Tables created: {tables}")
        for expected in ['users', 'datasets', 'sales_records', 'customers']:
            if expected not in tables:
                errors.append(f"Missing table: {expected}")

    with app.test_client() as client:
        # 2. Register page loads
        resp = client.get('/auth/register')
        assert resp.status_code == 200, f"Register page failed: {resp.status_code}"
        print("[OK] GET /auth/register -> 200")

        # 3. Login page loads
        resp = client.get('/auth/login')
        assert resp.status_code == 200, f"Login page failed: {resp.status_code}"
        print("[OK] GET /auth/login -> 200")

        # 4. Register a user
        resp = client.post('/auth/register', data={
            'email': 'test@example.com',
            'business_name': 'Test Corp',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
        }, follow_redirects=True)
        assert resp.status_code == 200
        print("[OK] POST /auth/register -> user created")

        # 6. Login
        resp = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'testpass123',
        }, follow_redirects=True)
        assert resp.status_code == 200
        print("[OK] POST /auth/login -> authenticated")

        # 7. Upload page accessible (logged in)
        resp = client.get('/datasets/upload')
        assert resp.status_code == 200
        print("[OK] GET /datasets/upload -> 200 (authenticated)")

        # 8. Upload a CSV
        csv_content = (
            "date,product,category,quantity,unit_price,region,customer_id\n"
            "2025-01-15,Widget A,Electronics,10,29.99,North,C001\n"
            "2025-01-16,Widget B,Home,5,49.99,South,C002\n"
            "2025-01-17,Widget A,Electronics,8,29.99,North,C001\n"
            "2025-02-01,Widget C,Electronics,3,99.99,East,C003\n"
            "2025-02-05,Widget B,Home,12,49.99,West,C004\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_sales.csv'),
            'industry_type': 'retail',
        }
        resp = client.post('/datasets/upload', data=data,
                          content_type='multipart/form-data',
                          follow_redirects=True)
        assert resp.status_code == 200
        print("[OK] POST /datasets/upload -> CSV uploaded")

        # 9. Check detail page loads (follows redirect from upload)
        resp = client.get('/datasets/1')
        assert resp.status_code == 200
        assert b'test_sales.csv' in resp.data
        print("[OK] GET /datasets/1 -> 200 (detail page)")

        # 10. Cross-account isolation
        client.get('/auth/logout')
        client.post('/auth/register', data={
            'email': 'other@example.com',
            'business_name': 'Other Inc',
            'password': 'otherpass123',
            'confirm_password': 'otherpass123',
        }, follow_redirects=True)
        client.post('/auth/login', data={
            'email': 'other@example.com',
            'password': 'otherpass123',
        }, follow_redirects=True)

        resp = client.get('/datasets/1', follow_redirects=True)
        response_text = resp.data.decode('utf-8')
        assert 'Access denied' in response_text
        print("[OK] Cross-account isolation: other user cannot access first user's dataset")

    # Verify DB contents outside of test_client
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.check_password('testpass123')
        print(f"[OK] User in DB: {user}")

        ds = Dataset.query.first()
        assert ds is not None and ds.status == 'ready' and ds.row_count == 5
        print(f"[OK] Dataset in DB: {ds} - {ds.row_count} rows, status={ds.status}")

        records = SalesRecord.query.filter_by(dataset_id=ds.id).all()
        assert len(records) == 5
        assert records[0].revenue is not None
        print(f"[OK] SalesRecords: {len(records)} rows, revenue[0]=${records[0].revenue:.2f}")

        customers = Customer.query.filter_by(dataset_id=ds.id).all()
        assert len(customers) == 4
        print(f"[OK] Customers extracted: {len(customers)}")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 1 -- ALL CHECKS PASSED")
        print(f"{'='*50}")


if __name__ == '__main__':
    test_phase1()

