"""Unit Tests for Analytics Engines (KPIs, Anomalies, RCA, and Forecasting)."""
import sys
import os
import io
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.dataset import Dataset
from app.models.sales import SalesRecord
from app.models.anomaly import Anomaly
from app.models.forecast import Forecast
from app.models.root_cause import RootCauseReport

from app.analytics.kpi_engine import get_kpis
from app.analytics.anomaly_detector import detect_anomalies
from app.root_cause.engine import analyze_root_cause
from app.forecasting.engine import generate_forecast

def setup_test_db(app):
    """Clean up and prepare database schema."""
    with app.app_context():
        db.drop_all()
        db.create_all()

def test_kpi_engine(app):
    print("Testing KPI Engine...")
    with app.app_context():
        # Setup test data
        user = User(email='kpi@example.com', business_name='KPI Corp')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        dataset = Dataset(original_filename='kpi_test.csv', status='ready', user_id=user.id, row_count=0)
        db.session.add(dataset)
        db.session.commit()

        # 1. Test empty KPIs
        empty_kpis = get_kpis(dataset.id)
        assert empty_kpis['total_revenue'] == 0
        assert empty_kpis['total_orders'] == 0
        assert empty_kpis['top_product'] is None
        assert empty_kpis['top_region'] is None
        print("  [✓] Empty dataset KPI check passed")

        # 2. Test calculated KPIs
        # Adding 6 sales records across a span of 3 days
        base_date = datetime(2025, 1, 1)
        records = [
            SalesRecord(dataset_id=dataset.id, date=(base_date).strftime('%Y-%m-%d'), revenue=100.0, quantity=2, product='Widget A', category='Category X', region='North', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date=(base_date).strftime('%Y-%m-%d'), revenue=200.0, quantity=4, product='Widget B', category='Category Y', region='South', customer_id='C2'),
            SalesRecord(dataset_id=dataset.id, date=(base_date + timedelta(days=1)).strftime('%Y-%m-%d'), revenue=150.0, quantity=3, product='Widget A', category='Category X', region='North', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date=(base_date + timedelta(days=1)).strftime('%Y-%m-%d'), revenue=50.0, quantity=1, product='Widget C', category='Category X', region='East', customer_id='C3'),
            # Second half starts here (index 2 onwards for midpoint logic)
            SalesRecord(dataset_id=dataset.id, date=(base_date + timedelta(days=2)).strftime('%Y-%m-%d'), revenue=300.0, quantity=6, product='Widget A', category='Category X', region='North', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date=(base_date + timedelta(days=2)).strftime('%Y-%m-%d'), revenue=400.0, quantity=8, product='Widget B', category='Category Y', region='South', customer_id='C2'),
        ]
        db.session.add_all(records)
        db.session.commit()

        # Refresh dataset row count
        dataset.row_count = 6
        db.session.commit()

        kpis = get_kpis(dataset.id)
        assert kpis['total_revenue'] == 1200.0
        assert kpis['total_orders'] == 6
        assert kpis['top_product'] == 'Widget B'  # Widget B revenue = 200 + 400 = 600; Widget A = 100+150+300 = 550
        assert kpis['top_region'] == 'South'      # South = 200 + 400 = 600; North = 100+150+300 = 550
        
        # Test Growth Pct
        # First half (3 records): 100 + 200 + 150 = 450
        # Second half (3 records): 50 + 300 + 400 = 750
        # Growth = (750 - 450) / 450 * 100 = 66.67%
        assert round(kpis['growth_pct'], 2) == 66.67
        
        # Test charts format
        assert 'labels' in kpis['chart_data']
        assert 'revenue' in kpis['chart_data']
        assert len(kpis['category_chart']['labels']) == 2
        print("  [✓] Populated dataset KPI check passed")

def test_anomaly_detector(app):
    print("Testing Anomaly Detector...")
    with app.app_context():
        user = User.query.first()
        dataset = Dataset(original_filename='anomaly_test.csv', status='ready', user_id=user.id, row_count=0)
        db.session.add(dataset)
        db.session.commit()

        # 1. Empty dataset anomalies
        anomalies = detect_anomalies(dataset.id)
        assert anomalies == []
        print("  [✓] Empty dataset anomalies check passed")

        # 2. Too short time series (<5 unique days)
        records = [
            SalesRecord(dataset_id=dataset.id, date='2025-01-01', revenue=100.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date='2025-01-02', revenue=100.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date='2025-01-03', revenue=100.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date='2025-01-04', revenue=100.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
        ]
        db.session.add_all(records)
        db.session.commit()
        anomalies = detect_anomalies(dataset.id)
        assert anomalies == []
        print("  [✓] Short dataset (<5 days) anomalies check passed")

        # 3. Detect clear outlier anomaly (>5 days, 1 massive spike)
        more_records = [
            SalesRecord(dataset_id=dataset.id, date='2025-01-05', revenue=100.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
            # Spike day
            SalesRecord(dataset_id=dataset.id, date='2025-01-06', revenue=5000.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date='2025-01-07', revenue=100.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
        ]
        db.session.add_all(more_records)
        db.session.commit()

        anomalies = detect_anomalies(dataset.id)
        assert len(anomalies) > 0
        anomaly_dates = [a['date'] for a in anomalies]
        assert '2025-01-06' in anomaly_dates
        spike_detail = next(a for a in anomalies if a['date'] == '2025-01-06')
        assert spike_detail['actual_value'] == 5000.0
        assert spike_detail['type'] == 'positive'
        print("  [✓] Anomaly spike detection check passed")

def test_root_cause_analysis(app):
    print("Testing Root Cause Analysis Engine...")
    with app.app_context():
        user = User.query.first()
        dataset = Dataset(original_filename='rca_test.csv', status='ready', user_id=user.id, row_count=0)
        db.session.add(dataset)
        db.session.commit()

        # Add baseline records for 10 days, selling Widget A and Widget B in North/South
        base_date = datetime(2025, 2, 1)
        records = []
        for i in range(10):
            d = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
            # Consistent sales
            records.append(SalesRecord(dataset_id=dataset.id, date=d, revenue=10.0, quantity=1, product='Widget A', category='CatX', region='North', customer_id='C1'))
            records.append(SalesRecord(dataset_id=dataset.id, date=d, revenue=20.0, quantity=2, product='Widget B', category='CatY', region='South', customer_id='C2'))
        
        # Anomaly Day - Widget B spiked massive in South, Widget A dropped to 0 (possible stockout)
        anomaly_date_str = '2025-02-15'
        records.append(SalesRecord(dataset_id=dataset.id, date=anomaly_date_str, revenue=1000.0, quantity=100, product='Widget B', category='CatY', region='South', customer_id='C2'))
        
        db.session.add_all(records)
        db.session.commit()

        # Create Anomaly record manually
        anomaly = Anomaly(
            dataset_id=dataset.id,
            dimension='date',
            dimension_value=anomaly_date_str,
            metric='revenue',
            method='z-score',
            observed_value=1000.0,
            expected_range_low=30.0,
            expected_range_high=30.0,
            severity='high',
            message='Statistical spike',
            type='positive'
        )
        db.session.add(anomaly)
        db.session.commit()

        # Analyze root cause
        rca_report = analyze_root_cause(dataset.id, anomaly.id)
        assert rca_report is not None
        assert rca_report['total_delta_pct'] > 0
        
        # Verify contributors
        contributors = rca_report['contributors']
        # Region South should be top positive contributor
        south_c = next((c for c in contributors if c.get('dimension') == 'region' and c.get('dimension_value') == 'South'), None)
        assert south_c is not None
        assert south_c['delta_value'] > 0
        
        # Widget A should be flagged as possible stockout (consistently sold, 0 on anomaly day)
        stockout_c = next((c for c in contributors if c.get('type') == 'possible_stockout'), None)
        assert stockout_c is not None
        assert stockout_c['dimension_value'] == 'Widget A'
        
        print("  [✓] RCA decomposition and heuristic checks passed")

def test_forecasting_engine(app):
    print("Testing Forecasting Engine...")
    with app.app_context():
        user = User.query.first()
        dataset = Dataset(original_filename='forecast_test.csv', status='ready', user_id=user.id, row_count=0)
        db.session.add(dataset)
        db.session.commit()

        # 1. Under 5 days test (should return None)
        under_5_records = [
            SalesRecord(dataset_id=dataset.id, date='2025-03-01', revenue=10.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
            SalesRecord(dataset_id=dataset.id, date='2025-03-02', revenue=15.0, quantity=1, product='P', category='C', region='R', customer_id='C1'),
        ]
        db.session.add_all(under_5_records)
        db.session.commit()
        
        assert generate_forecast(dataset.id) is None
        print("  [✓] Under 5 days forecast check passed")

        # Clean DB for next cases
        db.session.query(SalesRecord).filter_by(dataset_id=dataset.id).delete()
        db.session.commit()

        # 2. Trend model: Between 5 and 13 days of daily records
        base_date = datetime(2025, 3, 1)
        trend_records = []
        for i in range(8):
            d = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
            trend_records.append(SalesRecord(dataset_id=dataset.id, date=d, revenue=10.0 + i*2.0, quantity=1, product='P', category='C', region='R', customer_id='C1'))
        db.session.add_all(trend_records)
        db.session.commit()

        forecast = generate_forecast(dataset.id)
        assert forecast is not None
        assert forecast.model_used == 'exponential_smoothing_trend'
        assert len(forecast.forecast_json['dates']) == 30
        print("  [✓] Trend-only Holt-Winters model check passed")

        # Clean DB
        db.session.query(SalesRecord).filter_by(dataset_id=dataset.id).delete()
        db.session.commit()

        # 3. Seasonal model: >= 14 days of daily records
        seasonal_records = []
        for i in range(16):
            d = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
            # Let's create weekly pattern
            val = 20.0 + (5.0 if i % 7 == 0 else 0.0)
            seasonal_records.append(SalesRecord(dataset_id=dataset.id, date=d, revenue=val, quantity=1, product='P', category='C', region='R', customer_id='C1'))
        db.session.add_all(seasonal_records)
        db.session.commit()

        forecast_seasonal = generate_forecast(dataset.id)
        assert forecast_seasonal is not None
        assert forecast_seasonal.model_used == 'exponential_smoothing_seasonal'
        print("  [✓] Seasonal Holt-Winters model check passed")

        # 4. Fallback model: linear regression fallback when fitting fails
        # Let's trigger fallback by mocking ExponentialSmoothing to raise an exception
        with patch('app.forecasting.engine.ExponentialSmoothing') as mock_es:
            mock_es.side_effect = Exception("HW failed intentionally")
            forecast_fallback = generate_forecast(dataset.id)
            assert forecast_fallback is not None
            assert forecast_fallback.model_used == 'linear_regression_fallback'
            print("  [✓] Linear regression fallback model check passed")

def run_all_units():
    app = create_app('testing')
    setup_test_db(app)
    
    errors = []
    
    try:
        test_kpi_engine(app)
    except AssertionError as e:
        errors.append(f"KPI Engine failed: {e}")
        
    try:
        test_anomaly_detector(app)
    except AssertionError as e:
        errors.append(f"Anomaly Detector failed: {e}")
        
    try:
        test_root_cause_analysis(app)
    except AssertionError as e:
        errors.append(f"Root Cause Analysis failed: {e}")
        
    try:
        test_forecasting_engine(app)
    except AssertionError as e:
        errors.append(f"Forecasting Engine failed: {e}")

    if errors:
        print("\nUnit Test Failures:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("\n==================================================")
        print("ALL UNIT TESTS PASSED SUCCESSFULLY")
        print("==================================================")

if __name__ == '__main__':
    run_all_units()
