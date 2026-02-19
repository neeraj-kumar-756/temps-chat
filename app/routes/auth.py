import pyotp
import qrcode
from io import BytesIO
import base64
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import db
from app.models.database import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
        
        secret = pyotp.random_base32()
        new_user = User(username=username, secret=secret)
        db.session.add(new_user)
        db.session.commit()
        
        session['username_for_otp'] = username
        return redirect(url_for('auth.setup_mfa'))

    return render_template('auth/register.html')

@bp.route('/setup_mfa')
def setup_mfa():
    username = session.get('username_for_otp')
    if not username:
        return redirect(url_for('auth.register'))

    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('auth.register'))
    
    totp = pyotp.TOTP(user.secret)
    uri = totp.provisioning_uri(name=user.username, issuer_name='ChatApp')
    
    qr_img = qrcode.make(uri)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_str = buffered.getvalue()
    
    qr_code_data = base64.b64encode(img_str).decode('utf-8')
    
    return render_template('auth/setup_mfa.html', qr_code=qr_code_data)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        otp = request.form.get('otp')
        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Invalid username.', 'danger')
            return redirect(url_for('auth.login'))

        totp = pyotp.TOTP(user.secret)
        if totp.verify(otp):
            session['username'] = user.username
            return redirect(url_for('chat.lobby'))
        else:
            flash('Invalid OTP.', 'danger')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('channel_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
