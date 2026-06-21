"""Anomaly Detection Engine."""

import pandas as pd
import numpy as np
from ..models.sales import SalesRecord

def detect_anomalies(dataset_id, metric='revenue'):
    """
    Detect anomalies in a time series using Z-score and IQR.
    Returns a list of dictionaries with anomaly details.
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

    anomalies = []

    for idx, row in ts.iterrows():
        val = row[metric]
        z = z_scores[idx]
        
        is_anomaly = False
        severity = 'low'
        reason = ""

        # Check Z-score
        if abs(z) > 2.5:
            is_anomaly = True
            severity = 'high' if abs(z) > 3.5 else 'medium'
            direction = "spike" if z > 0 else "drop"
            reason = f"Statistical {direction} (Z-score: {z:.2f})"
        
        # Check IQR if not already flagged
        elif val < lower_bound or val > upper_bound:
            is_anomaly = True
            severity = 'low'
            direction = "spike" if val > upper_bound else "drop"
            reason = f"Outside expected range (IQR method)"

        if is_anomaly:
            expected_avg = mean_val
            diff_pct = ((val - expected_avg) / expected_avg) * 100 if expected_avg > 0 else 0

            anomalies.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'actual_value': float(val),
                'expected_value': float(expected_avg),
                'diff_pct': float(diff_pct),
                'severity': severity,
                'reason': reason,
                'type': 'positive' if val > expected_avg else 'negative'
            })

    # Sort anomalies descending by date (most recent first)
    anomalies.sort(key=lambda x: x['date'], reverse=True)
    return anomalies
