"""Automated Root Cause Analysis Engine.

Performs variance-decomposition (waterfall) analysis and heuristic signal detection.
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from ..models.sales import SalesRecord
from ..models.anomaly import Anomaly
from ..models.root_cause import RootCauseReport
from ..extensions import db

def analyze_root_cause(dataset_id, anomaly_id):
    """
    Decomposes the metric variance for a given anomaly against a baseline period.
    Returns the RootCauseReport dictionary.
    """
    # Check if a report already exists for this anomaly
    existing_report = RootCauseReport.query.filter_by(anomaly_id=anomaly_id).first()
    if existing_report:
        return {
            'id': existing_report.id,
            'total_delta_pct': existing_report.total_delta_pct,
            'contributors': existing_report.contributors_json
        }

    anomaly = Anomaly.query.get(anomaly_id)
    if not anomaly or anomaly.dataset_id != dataset_id:
        return None

    # We assume 'date' is our primary dimension for time
    anomaly_date_str = anomaly.dimension_value
    anomaly_date = pd.to_datetime(anomaly_date_str)
    
    # Baseline window: 30 days prior to the anomaly date
    # If the dataset doesn't have 30 days, we'll use whatever history is available
    start_baseline = anomaly_date - timedelta(days=30)
    end_baseline = anomaly_date - timedelta(days=1)

    records = SalesRecord.query.filter_by(dataset_id=dataset_id).all()
    if not records:
        return None

    df = pd.DataFrame([{
        'date': pd.to_datetime(r.date),
        'revenue': r.revenue or 0,
        'quantity': r.quantity or 0,
        'region': r.region or 'Unknown',
        'product': r.product or 'Unknown',
        'category': r.category or 'Unknown',
        'customer_id': r.customer_id
    } for r in records])

    # Filter into current vs baseline
    df_current = df[df['date'] == anomaly_date]
    df_baseline = df[(df['date'] >= start_baseline) & (df['date'] <= end_baseline)]

    num_baseline_days = df_baseline['date'].nunique()
    if num_baseline_days == 0:
        # Cannot do RCA without a baseline
        return None

    metric = anomaly.metric  # e.g., 'revenue'
    
    # Baseline averages per day
    baseline_avg_total = df_baseline[metric].sum() / num_baseline_days
    current_total = df_current[metric].sum()
    
    delta_total = current_total - baseline_avg_total
    
    if baseline_avg_total > 0:
        total_delta_pct = (delta_total / baseline_avg_total) * 100
    else:
        total_delta_pct = 100.0 if delta_total > 0 else 0.0

    contributors = []

    # Guardrail: minimum baseline orders to be eligible for ranking
    min_volume = 1.0  # Just needs at least some presence in the baseline to avoid 100% swings on tiny data

    dimensions = ['region', 'category', 'product']
    
    for dim in dimensions:
        # Group by dimension for current and baseline
        curr_grouped = df_current.groupby(dim)[metric].sum().to_dict()
        base_grouped = (df_baseline.groupby(dim)[metric].sum() / num_baseline_days).to_dict()
        base_volume = (df_baseline.groupby(dim)['quantity'].sum() / num_baseline_days).to_dict()

        all_keys = set(curr_grouped.keys()).union(set(base_grouped.keys()))

        for key in all_keys:
            c_val = curr_grouped.get(key, 0)
            b_val = base_grouped.get(key, 0)
            b_vol = base_volume.get(key, 0)

            if b_vol < min_volume and c_val == 0:
                continue # Skip low-volume noise if it didn't spike

            delta_d = c_val - b_val
            
            # Avoid division by zero if delta_total is 0
            if delta_total != 0:
                # We rank contributors whose delta matches the direction of the anomaly
                # If anomaly is a spike (positive delta), positive contributors pushed it up.
                # If anomaly is a drop (negative delta), negative contributors pushed it down.
                # Only care if direction matches
                if (delta_total > 0 and delta_d > 0) or (delta_total < 0 and delta_d < 0):
                    contribution_pct = (delta_d / delta_total) * 100
                    contributors.append({
                        'dimension': dim,
                        'dimension_value': key,
                        'delta_value': delta_d,
                        'contribution_pct': round(contribution_pct, 1)
                    })

    # Sort contributors descending by contribution_pct
    contributors.sort(key=lambda x: x['contribution_pct'], reverse=True)

    # Candidate Signals (Heuristics)
    
    # 1. Stockout heuristic
    # A product that had consistent baseline sales but 0 sales on the anomaly day
    for key in set(df_baseline['product'].unique()):
        b_vol = base_volume.get(key, 0)
        c_vol = df_current[df_current['product'] == key]['quantity'].sum()
        if b_vol > 0.5 and c_vol == 0: # If it averaged at least 0.5 units/day but sold 0
            contributors.append({
                'type': 'possible_stockout',
                'dimension': 'product',
                'dimension_value': key,
                'confidence': 'heuristic'
            })

    # 2. Churn heuristic
    # Customers present in baseline but not in current
    base_customers = set(df_baseline['customer_id'].unique())
    curr_customers = set(df_current['customer_id'].unique())
    
    churned_customers = base_customers - curr_customers
    # We only flag churn if there's a significant drop
    if delta_total < 0 and len(churned_customers) > 0:
        # Instead of listing all, just group them
        contributors.append({
            'type': 'churn_risk',
            'dimension': 'customer_id',
            'dimension_value': f"{len(churned_customers)} customers",
            'confidence': 'heuristic'
        })

    # Persist the report
    report = RootCauseReport(
        dataset_id=dataset_id,
        anomaly_id=anomaly_id,
        period_current=anomaly_date_str,
        period_baseline=f"{num_baseline_days}-day avg",
        metric=metric,
        total_delta_pct=total_delta_pct,
        contributors_json=contributors
    )
    db.session.add(report)
    db.session.commit()

    return {
        'id': report.id,
        'total_delta_pct': total_delta_pct,
        'contributors': contributors
    }
