from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, stream_with_context
from flask_login import login_user, logout_user, login_required, current_user
import secrets
import requests
from . import db
from .models import User, ProxyConfig
from .crypto_utils import encrypt_token, decrypt_token

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('main.login'))
        login_user(user)
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        kobo_key = request.form['kobo_key']
        # Determine Kobo Server (defaulting to standard for now, could be a form field later)
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('main.register'))
            
        user = User(email=email, encrypted_kobo_token=encrypt_token(kobo_key))
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('main.dashboard'))
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    proxies = ProxyConfig.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', proxies=proxies)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_proxy():
    if request.method == 'POST':
        name = request.form['name']
        asset_uid = request.form['asset_uid']
        setting_uid = request.form['setting_uid']
        
        # Generate a random 32-char hex token
        token = secrets.token_hex(16)
        
        proxy = ProxyConfig(
            user_id=current_user.id,
            name=name,
            token=token,
            asset_uid=asset_uid,
            setting_uid=setting_uid
        )
        db.session.add(proxy)
        db.session.commit()
        flash('Proxy configuration created!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('create.html')

@bp.route('/delete/<int:id>')
@login_required
def delete_proxy(id):
    proxy = ProxyConfig.query.get_or_404(id)
    if proxy.user_id != current_user.id:
        return "Unauthorized", 403
    db.session.delete(proxy)
    db.session.commit()
    flash('Proxy deleted', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/exports/<asset_uid>/<setting_uid>/<fmt>')
def proxy_export(asset_uid, setting_uid, fmt):
    token = request.args.get('token')
    if not token:
        return "Missing token", 401
        
    config = ProxyConfig.query.filter_by(token=token).first()
    if not config:
        return "Invalid token", 403
        
    if config.asset_uid != asset_uid or config.setting_uid != setting_uid:
        return "Asset/Setting mismatch for this token", 403
        
    try:
        user_kobo_key = decrypt_token(config.user.encrypted_kobo_token)
    except Exception as e:
        return f"Encryption Error: {str(e)}", 500
    
    # KoboToolbox V2 API Export URL
    # Assuming kf.kobotoolbox.org.
    # If users are on other instances, we might need to store 'kobo_server_url' in User model.
    base_url = "https://kf.kobotoolbox.org"
    kobo_url = f"{base_url}/api/v2/assets/{asset_uid}/export-settings/{setting_uid}/data.{fmt}"
    
    headers = {
        'Authorization': f'Token {user_kobo_key}'
    }
    
    # Forward the request
    req = requests.get(kobo_url, headers=headers, stream=True)
    
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in req.headers.items()
               if name.lower() not in excluded_headers]

    return Response(stream_with_context(req.iter_content(chunk_size=4096)),
                    status=req.status_code,
                    content_type=req.headers.get('content-type'),
                    headers=headers)
