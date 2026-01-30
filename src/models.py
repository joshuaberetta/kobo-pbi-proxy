from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

from datetime import datetime, timezone

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    kobo_server = db.Column(db.String(255), default='https://kf.kobotoolbox.org')
    kobo_username = db.Column(db.String(120))
    encrypted_kobo_token = db.Column(db.LargeBinary)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ProxyConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(64), unique=True, index=True, nullable=False)
    asset_uid = db.Column(db.String(100), nullable=False)
    setting_uid = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('proxies', lazy=True))
