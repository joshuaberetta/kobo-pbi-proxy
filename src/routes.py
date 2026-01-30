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
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return redirect(url_for('main.login'))
        login_user(user)
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@bp.route('/api/verify-token', methods=['POST'])
def verify_token_api():
    data = request.get_json()
    kobo_server = data.get('kobo_server', '').rstrip('/')
    kobo_key = data.get('kobo_key', '')
    
    if not kobo_server or not kobo_key:
        return {'success': False, 'message': 'Missing server or token'}, 400
        
    try:
        verify_url = f"{kobo_server}/me/"
        headers = {'Authorization': f'Token {kobo_key}'}
        resp = requests.get(verify_url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            kobo_user_data = resp.json()
            # The /me/ endpoint returns { "username": "...", ... }
            return {
                'success': True, 
                'username': kobo_user_data.get('username', 'Unknown')
            }
        else:
            return {
                'success': False, 
                'message': f'Server returned {resp.status_code}'
            }, 400
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        kobo_key = request.form['kobo_key']
        kobo_server = request.form.get('kobo_server', 'https://kf.kobotoolbox.org').rstrip('/')
        
        # Verify Kobo Connection
        kobo_username = None
        try:
            # We use the 'me' endpoint which exists on both kf.kobotoolbox.org and eu.kobotoolbox.org
            # It requires Token auth
            verify_url = f"{kobo_server}/me/"
            headers = {'Authorization': f'Token {kobo_key}'}
            resp = requests.get(verify_url, headers=headers, timeout=5)
            
            if resp.status_code != 200:
                flash(f'Failed to verify Kobo Token against {kobo_server}. Kobo said: {resp.status_code}', 'error')
                return redirect(url_for('main.register'))
            
            # Extract Kobo username
            kobo_username = resp.json().get('username')
            
        except Exception as e:
            flash(f'Connection error verifying Kobo Token: {str(e)}', 'error')
            return redirect(url_for('main.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already registered', 'error')
            return redirect(url_for('main.register'))
            
        user = User(
            username=username, 
            encrypted_kobo_token=encrypt_token(kobo_key),
            kobo_server=kobo_server,
            kobo_username=kobo_username
        )
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

@bp.route('/help')
def help():
    return render_template('help.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    query = request.args.get('q', '')
    proxy_query = ProxyConfig.query.filter_by(user_id=current_user.id)
    
    if query:
        proxy_query = proxy_query.filter(ProxyConfig.asset_uid.contains(query))
        
    proxies = proxy_query.order_by(ProxyConfig.created_at.desc()).all()
    return render_template('dashboard.html', proxies=proxies, query=query)

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
    return render_template('create.html', title="Create New Proxy", btn_label="Create Proxy", proxy=None)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_proxy(id):
    proxy = ProxyConfig.query.get_or_404(id)
    if proxy.user_id != current_user.id:
        return "Unauthorized", 403

    if request.method == 'POST':
        proxy.name = request.form['name']
        proxy.asset_uid = request.form['asset_uid']
        proxy.setting_uid = request.form['setting_uid']
        db.session.commit()
        flash('Proxy configuration updated!', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('create.html', title="Edit Proxy", btn_label="Update Proxy", proxy=proxy)

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
        # Use user's configured server
        base_url = config.user.kobo_server
    except Exception as e:
        return f"Encryption/Config Error: {str(e)}", 500
    
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
