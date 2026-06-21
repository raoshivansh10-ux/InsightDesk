"""Health Score Module — computes a holistic business health score out of 100."""


def calculate_health_score(growth_pct, retention_rate=None, forecast_outlook=None):
    """
    Calculate business health score (0-100).
    Formula: 0.4 * growth + 0.3 * retention + 0.3 * forecast (simplified)
    
    If retention or forecast are missing (e.g. Phase 2), weights are redistributed.
    """
    # Normalize growth: Cap at 50% for scoring purposes (-50 to +50 map to 0 to 100)
    # 0% growth = 50 points
    norm_growth = max(0, min(100, 50 + growth_pct))

    score_components = []
    
    # Base score on growth if it's the only metric available
    score = norm_growth
    score_components.append({'name': 'Growth Outlook', 'value': f"{growth_pct:.1f}%", 'score': norm_growth})

    if retention_rate is not None:
        # Retention out of 100
        score = (score * 0.6) + (retention_rate * 0.4)
        score_components.append({'name': 'Retention', 'value': f"{retention_rate:.1f}%", 'score': retention_rate})

    if forecast_outlook is not None:
        # Forecast mapped to 0-100
        score = (score * 0.7) + (forecast_outlook * 0.3)
        score_components.append({'name': 'Forecast Outlook', 'value': "Computed", 'score': forecast_outlook})

    score = min(100, max(0, score))
    
    if score >= 80:
        label = "Strong"
        color_class = "success"
    elif score >= 65:
        label = "Good"
        color_class = "info"
    elif score >= 50:
        label = "Average"
        color_class = "warning"
    else:
        label = "Weak"
        color_class = "danger"

    return {
        'score': int(score),
        'label': label,
        'color_class': color_class,
        'components': score_components
    }
