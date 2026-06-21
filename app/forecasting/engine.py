import pandas as pd
import numpy as np
from datetime import timedelta
from app.extensions import db
from app.models.sales import SalesRecord
from app.models.forecast import Forecast
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.linear_model import LinearRegression

def generate_forecast(dataset_id, horizon_days=30):
    """
    Generate a revenue forecast for the given dataset.
    Returns the forecast object if successful, None otherwise.
    """
    # 1. Fetch historical daily revenue
    records = db.session.query(
        db.func.date(SalesRecord.date).label('date'),
        db.func.sum(SalesRecord.revenue).label('revenue')
    ).filter(SalesRecord.dataset_id == dataset_id)\
     .group_by(db.func.date(SalesRecord.date))\
     .order_by(db.func.date(SalesRecord.date)).all()

    if len(records) < 5:
        # Not enough data to forecast reliably
        return None

    # Convert to pandas series
    dates = [r.date for r in records]
    revenues = [float(r.revenue) for r in records]
    df = pd.DataFrame({'date': pd.to_datetime(dates), 'revenue': revenues})
    df.set_index('date', inplace=True)
    df = df.asfreq('D') # Ensure daily frequency
    df['revenue'] = df['revenue'].fillna(0) # Fill missing days with 0

    ts = df['revenue']

    # 2. Train Model
    # Choose model complexity based on data length
    # If >= 14 days, use weekly seasonality. Otherwise, just trend.
    has_seasonality = len(ts) >= 14
    
    try:
        if has_seasonality:
            model = ExponentialSmoothing(
                ts, 
                trend='add', 
                seasonal='add', 
                seasonal_periods=7, 
                initialization_method="estimated"
            ).fit()
            model_used = 'exponential_smoothing_seasonal'
        else:
            model = ExponentialSmoothing(
                ts, 
                trend='add', 
                seasonal=None, 
                initialization_method="estimated"
            ).fit()
            model_used = 'exponential_smoothing_trend'
            
        forecast_vals = model.forecast(horizon_days)
        
        # Approximate confidence intervals using residuals standard error
        residuals = model.resid
        std_error = np.std(residuals)
        
        # 1.96 for 95% confidence
        upper_bound = forecast_vals + (1.96 * std_error)
        lower_bound = forecast_vals - (1.96 * std_error)
        lower_bound = np.maximum(lower_bound, 0) # Revenue can't be negative
        
    except Exception as e:
        # Fallback to Simple Linear Regression if Holt-Winters fails
        print(f"Holt-Winters failed, falling back to LinearRegression: {e}")
        X = np.arange(len(ts)).reshape(-1, 1)
        y = ts.values
        lr = LinearRegression().fit(X, y)
        
        X_pred = np.arange(len(ts), len(ts) + horizon_days).reshape(-1, 1)
        forecast_vals = pd.Series(lr.predict(X_pred), index=[ts.index[-1] + timedelta(days=i) for i in range(1, horizon_days + 1)])
        
        std_error = np.std(y - lr.predict(X))
        upper_bound = forecast_vals + (1.96 * std_error)
        lower_bound = np.maximum(forecast_vals - (1.96 * std_error), 0)
        model_used = 'linear_regression_fallback'

    # 3. Calculate Outlook Score (Trend Slope)
    # We define outlook score as the expected growth percentage over the horizon
    start_val = max(forecast_vals.iloc[0], 1)
    end_val = forecast_vals.iloc[-1]
    outlook_score = ((end_val - start_val) / start_val) * 100.0

    # Cap the outlook score
    outlook_score = max(min(outlook_score, 100.0), -100.0)

    # 4. Prepare JSON Payload
    last_date = ts.index[-1]
    forecast_dates = [(last_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, horizon_days + 1)]
    
    forecast_json = {
        'dates': forecast_dates,
        'predicted_values': [round(x, 2) for x in forecast_vals.values],
        'lower_bounds': [round(x, 2) for x in lower_bound],
        'upper_bounds': [round(x, 2) for x in upper_bound]
    }

    # 5. Save to DB
    # Check if we already have a forecast for this dataset to update, otherwise create new
    existing = Forecast.query.filter_by(dataset_id=dataset_id).first()
    
    if existing:
        existing.generated_at = db.func.now()
        existing.model_used = model_used
        existing.horizon_days = horizon_days
        existing.forecast_json = forecast_json
        existing.outlook_score = outlook_score
        forecast_obj = existing
    else:
        forecast_obj = Forecast(
            dataset_id=dataset_id,
            model_used=model_used,
            horizon_days=horizon_days,
            forecast_json=forecast_json,
            outlook_score=outlook_score
        )
        db.session.add(forecast_obj)
        
    db.session.commit()
    return forecast_obj
