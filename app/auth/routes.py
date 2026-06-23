"""Auth routes — register, login, logout."""

from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from .forms import RegisterForm, LoginForm
from ..extensions import db
from ..models.user import User
from ..supabase_config import supabase


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if supabase is None:
        # Fallback to local SQLite Auth
        if current_user.is_authenticated:
            return redirect(url_for('ingestion.upload'))

        form = RegisterForm()
        if form.validate_on_submit():
            user = User(
                email=form.email.data.lower().strip(),
                business_name=form.business_name.data.strip() or None
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully. Please sign in.', 'success')
            return redirect(url_for('auth.login'))

        return render_template('register.html', form=form)

    # Supabase Auth Integration
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            # Register using Supabase SDK
            response = supabase.auth.sign_up({
                "email": form.email.data.lower().strip(),
                "password": form.password.data,
                "options": {
                    "data": {
                        "business_name": form.business_name.data.strip() or 'My Business'
                    }
                }
            })
            
            # Sync user inside database
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if not user:
                user = User(
                    email=form.email.data.lower().strip(),
                    business_name=form.business_name.data.strip() or 'My Business',
                    password_hash='SUPABASE_EXTERNAL_AUTH'
                )
                db.session.add(user)
                db.session.commit()

            flash('Account created successfully. Please check your email for verification link.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')

    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if supabase is None:
        # Fallback to local SQLite Auth
        if current_user.is_authenticated:
            return redirect(url_for('ingestion.upload'))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Welcome back!', 'success')
                return redirect(next_page or url_for('ingestion.upload'))
            flash('Invalid email or password.', 'danger')

        return render_template('login.html', form=form)

    # Supabase Auth Integration
    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Sign in with password using Supabase SDK
            response = supabase.auth.sign_in_with_password({
                "email": form.email.data.lower().strip(),
                "password": form.password.data
            })
            
            # Store JWT session and user id in Flask session
            session['access_token'] = response.session.access_token
            session['user_id'] = response.user.id
            
            # Get user from DB or sync
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if not user:
                user = User(
                    email=response.user.email,
                    business_name=response.user.user_metadata.get('business_name', 'My Business') if response.user.user_metadata else 'My Business',
                    password_hash='SUPABASE_EXTERNAL_AUTH'
                )
                db.session.add(user)
                db.session.commit()

            login_user(user)
            
            next_page = request.args.get('next')
            flash('Welcome back!', 'success')
            return redirect(next_page or url_for('ingestion.upload'))
        except Exception as e:
            flash(f'Invalid email or password: {str(e)}', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    if supabase is None:
        # Fallback to local SQLite Auth
        logout_user()
        flash('You have been signed out.', 'info')
        return redirect(url_for('auth.login'))

    # Supabase Auth Sign out
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    logout_user()
    session.clear()
    flash('You have been signed out.', 'info')
    return redirect(url_for('auth.login'))
