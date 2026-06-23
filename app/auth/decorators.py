from functools import wraps
from flask import request, jsonify, g
from app.supabase_config import supabase
from flask_login import current_user
from app.models.user import User
from app.extensions import db

def require_supabase_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Fallback for local development/testing if Supabase client is not initialized
        if supabase is None:
            if current_user and current_user.is_authenticated:
                g.user = current_user
                return f(*args, **kwargs)
            try:
                local_user = User.query.first()
                if local_user:
                    g.user = local_user
                    if not current_user or not current_user.is_authenticated:
                        from flask_login import login_user
                        login_user(local_user)
                    return f(*args, **kwargs)
            except Exception:
                pass
            return jsonify({'error': 'Local database is empty and Supabase is not configured.'}), 401

        token = None
        # Read Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization'].split(" ")
            if len(auth_header) == 2:
                token = auth_header[1]
                
        if not token:
            from flask import session
            token = session.get('access_token')

        if not token:
            # Fallback to Flask-Login session if available
            if current_user and current_user.is_authenticated:
                g.user = current_user
                return f(*args, **kwargs)
            return jsonify({'error': 'Authorization token is missing'}), 401
            
        try:
            # Verify token with Supabase Auth
            user_response = supabase.auth.get_user(token)
            # Find matching user in database by email
            user = User.query.filter_by(email=user_response.user.email).first()
            if not user:
                # Lazy create user if they registered via frontend directly but don't exist in DB
                user = User(
                    email=user_response.user.email,
                    business_name=user_response.user.user_metadata.get('business_name', 'My Business') if user_response.user.user_metadata else 'My Business',
                    password_hash='SUPABASE_EXTERNAL_AUTH' # not used for auth
                )
                db.session.add(user)
                db.session.commit()
            
            # Log in user so current_user works in all Flask route handlers
            if not current_user or not current_user.is_authenticated or current_user.email != user.email:
                from flask_login import login_user
                login_user(user)
            g.user = user
        except Exception as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
            
        return f(*args, **kwargs)
    return decorated
