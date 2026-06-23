import time
from functools import wraps
from flask import request, jsonify, current_app

_rate_limits = {}

def rate_limit(limit=60, period=60):
    """
    In-memory sliding window rate limiter decorator.
    
    limit: max requests allowed in the window
    period: window size in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_app.config.get('TESTING') or current_app.config.get('DEBUG') and request.args.get('skip_limiter') == '1':
                return f(*args, **kwargs)

            ip = request.remote_addr or '127.0.0.1'
            endpoint = request.endpoint or 'unknown'
            key = f"{ip}:{endpoint}"
            
            now = time.time()
            
            # Filter out timestamps older than the rolling window
            timestamps = _rate_limits.get(key, [])
            timestamps = [t for t in timestamps if now - t < period]
            
            if len(timestamps) >= limit:
                current_app.logger.warning(f"Rate limit exceeded for IP: {ip} on endpoint: {endpoint}")
                return jsonify({
                    'error': 'Too Many Requests',
                    'message': f'Rate limit of {limit} requests per {period} seconds exceeded. Please try again.'
                }), 429
                
            timestamps.append(now)
            _rate_limits[key] = timestamps
            return f(*args, **kwargs)
        return wrapped
    return decorator
