"""KPI Engine — computes core business metrics from a dataset."""

import pandas as pd
from ..extensions import db
from ..models.sales import SalesRecord


def get_kpis(dataset_id):
    """Calculate aggregate KPIs for a dataset."""
    records = SalesRecord.query.filter_by(dataset_id=dataset_id).all()
    if not records:
        return _empty_kpis()

    # Convert to DataFrame for easier aggregation
    df = pd.DataFrame([{
        'date': r.date,
        'revenue': r.revenue or 0,
        'quantity': r.quantity or 0,
        'product': r.product or 'Unknown',
        'category': r.category or 'Unknown',
        'region': r.region or 'Unknown',
        'customer_id': r.customer_id
    } for r in records])

    # Convert date strings to datetime if necessary
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    total_revenue = float(df['revenue'].sum())
    total_orders = len(df)
    
    # Calculate simple growth: comparing second half of the time period to the first half
    midpoint_idx = len(df) // 2
    if midpoint_idx > 0:
        first_half_revenue = float(df.iloc[:midpoint_idx]['revenue'].sum())
        second_half_revenue = float(df.iloc[midpoint_idx:]['revenue'].sum())
        if first_half_revenue > 0:
            growth_pct = ((second_half_revenue - first_half_revenue) / first_half_revenue) * 100
        else:
            growth_pct = 0.0
    else:
        growth_pct = 0.0

    # Top dimensions
    top_product = df.groupby('product')['revenue'].sum().idxmax() if not df.empty else None
    top_region = df.groupby('region')['revenue'].sum().idxmax() if not df.empty else None

    # Time series for charts (monthly/daily depending on span)
    span_days = (df['date'].max() - df['date'].min()).days
    if span_days > 60:
        # Aggregate monthly
        time_series = df.set_index('date').resample('ME')['revenue'].sum().reset_index()
        time_series['date'] = time_series['date'].dt.strftime('%Y-%m')
    else:
        # Aggregate daily
        time_series = df.groupby(df['date'].dt.strftime('%Y-%m-%d'))['revenue'].sum().reset_index()
    
    chart_data = {
        'labels': time_series['date'].tolist(),
        'revenue': time_series['revenue'].tolist()
    }

    # Revenue by Category for charts
    category_revenue = df.groupby('category')['revenue'].sum().reset_index()
    category_chart = {
        'labels': category_revenue['category'].tolist(),
        'revenue': category_revenue['revenue'].tolist()
    }

    return {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'growth_pct': growth_pct,
        'top_product': top_product,
        'top_region': top_region,
        'chart_data': chart_data,
        'category_chart': category_chart
    }


def _empty_kpis():
    return {
        'total_revenue': 0,
        'total_orders': 0,
        'growth_pct': 0,
        'top_product': None,
        'top_region': None,
        'chart_data': {'labels': [], 'revenue': []},
        'category_chart': {'labels': [], 'revenue': []}
    }
