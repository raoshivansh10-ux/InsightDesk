"""Test for Forecasting Module (Phase 7)."""
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
from app.models.forecast import Forecast
from app.forecasting.engine import generate_forecast

def test_phase7():
    app = create_app('testing')
    errors = []

    with app.test_client() as client:
        # Setup a user
        client.post('/auth/register', data={
            'email': 'forecast@example.com',
            'business_name': 'Forecast Corp',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        
        client.post('/auth/login', data={
            'email': 'forecast@example.com',
            'password': 'password123',
        }, follow_redirects=True)

        # Generate 20 days of data to trigger the seasonal model
        csv_lines = ["date,product,category,quantity,unit_price,region,customer_id"]
        start_date = datetime(2025, 1, 1)
        for i in range(20):
            current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            # Add some sine wave seasonality
            qty = 10 + (i % 7) * 2
            csv_lines.append(f"{current_date},Widget A,Electronics,{qty},10.0,North,C001")
            
        csv_content = "\n".join(csv_lines) + "\n"
        
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'forecast_sales.csv'),
            'industry_type': 'retail',
        }
        client.post('/datasets/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        # Test 1: Generate Forecast via engine
        with app.app_context():
            # Dataset ID should be 1
            forecast = generate_forecast(1)
            
            if not forecast:
                errors.append("Forecast engine returned None!")
            else:
                print(f"[OK] Forecast generated. Model used: {forecast.model_used}")
                if forecast.model_used != 'exponential_smoothing_seasonal':
                    errors.append(f"Expected seasonal model, got {forecast.model_used}")
                else:
                    print("[OK] Seasonal model automatically selected for >= 14 days data.")
                    
                print(f"[OK] Outlook score: {forecast.outlook_score:.2f}%")
                
            # Verify DB persistence
            db_forecast = Forecast.query.filter_by(dataset_id=1).first()
            if not db_forecast:
                errors.append("Forecast not persisted to database!")
            else:
                print(f"[OK] Forecast saved to DB with ID: {db_forecast.id}")
                
        # Test 2: Fetch via Charts API
        resp = client.get('/dashboard/api/1/charts')
        assert resp.status_code == 200, f"Failed to fetch charts: {resp.status_code}"
        
        data = json.loads(resp.data)
        if not data.get('forecast'):
            errors.append("Forecast missing from charts API response!")
        else:
            fc = data['forecast']
            if len(fc['dates']) != 30:
                errors.append(f"Expected 30 forecasted days, got {len(fc['dates'])}")
            else:
                print("[OK] Charts API successfully returned 30-day forecast payload.")
                print(f"      First predicted date: {fc['dates'][0]}, value: ${fc['predicted_values'][0]}")

    if errors:
        print(f"\nFAILURES: {errors}")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("Phase 7 -- ALL CHECKS PASSED")
        print(f"{'='*50}")

if __name__ == '__main__':
    test_phase7()
