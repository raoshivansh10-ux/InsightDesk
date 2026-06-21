"""Anomaly Detection Engine."""

import pandas as pd
import numpy as np
from ..models.sales import SalesRecord
from ..models.anomaly import Anomaly
from ..extensions import db
from datetime import datetime

def detect_anomalies(dataset_id, metric='revenue'):
    """
    Detect anomalies in a time series using Z-score and IQR.
    Persists them to the DB and returns a list of dictionaries with anomaly details.
    """
    records = SalesRecord.query.filter_by(dataset_id=dataset_id).all()
    if not records:
        return []

    # Prepare time series data
    df = pd.DataFrame([{
        'date': r.date,
        'revenue': r.revenue or 0,
        'quantity': r.quantity or 0
    } for r in records])

    df['date'] = pd.to_datetime(df['date'])
    
    # Aggregate by day
    ts = df.groupby('date')[metric].sum().reset_index()
    ts = ts.sort_values('date')

    if len(ts) < 5:
        # Not enough data for meaningful anomaly detection
        return []

    values = ts[metric].values

    # --- Z-Score Method ---
    mean_val = np.mean(values)
    std_val = np.std(values)
    if std_val == 0:
        std_val = 1e-9 # avoid division by zero

    z_scores = (values - mean_val) / std_val

    # --- IQR Method ---
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    new_anomalies = []
    
    # Query existing anomalies to avoid duplicates
    existing_anomalies = Anomaly.query.filter_by(dataset_id=dataset_id, metric=metric, dimension='date').all()
    existing_dates = {a.dimension_value for a in existing_anomalies}

    for idx, row in ts.iterrows():
        val = row[metric]
        z = z_scores[idx]
        
        is_anomaly = False
        severity = 'low'
        reason = ""
        method_used = ""

        # Check Z-score
        if abs(z) > 2.5:
            is_anomaly = True
            severity = 'high' if abs(z) > 3.5 else 'medium'
            direction = "spike" if z > 0 else "drop"
            reason = f"Statistical {direction} (Z-score: {z:.2f})"
            method_used = "z-score"
        
        # Check IQR if not already flagged
        elif val < lower_bound or val > upper_bound:
            is_anomaly = True
            severity = 'low'
            direction = "spike" if val > upper_bound else "drop"
            reason = f"Outside expected range (IQR method)"
            method_used = "iqr"

        if is_anomaly:
            date_str = row['date'].strftime('%Y-%m-%d')
            expected_avg = mean_val
            diff_pct = ((val - expected_avg) / expected_avg) * 100 if expected_avg > 0 else 0
            is_positive = val > expected_avg

            # Persist to DB if not already exists
            if date_str not in existing_dates:
                anomaly_record = Anomaly(
                    dataset_id=dataset_id,
                    dimension='date',
                    dimension_value=date_str,
                    metric=metric,
                    method=method_used,
                    observed_value=float(val),
                    expected_range_low=float(mean_val) if method_used == 'z-score' else float(lower_bound),
                    expected_range_high=float(mean_val) if method_used == 'z-score' else float(upper_bound),
                    severity=severity,
                    message=reason,
                    type='positive' if is_positive else 'negative'
                )
                db.session.add(anomaly_record)
                new_anomalies.append(anomaly_record)

    if new_anomalies:
        db.session.commit()

    # Refetch all anomalies for this dataset/metric to return the full list
    all_anomalies = Anomaly.query.filter_by(dataset_id=dataset_id, metric=metric, dimension='date').all()
    
    result = []
    for a in all_anomalies:
        # Calculate diff_pct dynamically for backward compatibility with tests
        expected_val = a.expected_range_low  # Using the baseline for simple diff
        diff_pct = ((a.observed_value - expected_val) / expected_val) * 100 if expected_val > 0 else 0
        
        result.append({
            'id': a.id,
            'date': a.dimension_value,
            'actual_value': a.observed_value,
            'expected_value': expected_val,
            'diff_pct': diff_pct,
            'severity': a.severity,
            'reason': a.message,
            'type': a.type
        })

    # Sort anomalies descending by date (most recent first)
    result.sort(key=lambda x: x['date'], reverse=True)
    return result
