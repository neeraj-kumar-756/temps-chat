import uuid
import string
import random
from flask import Blueprint, render_template, session, redirect, url_for, current_app, flash, request
from app import socketio
from flask_socketio import emit, join_room, leave_room

bp = Blueprint('chat', __name__)

active_rooms = {}

def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@bp.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat.lobby'))
    return redirect(url_for('auth.login'))

@bp.route('/lobby', methods=['GET', 'POST'])
def lobby():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        if 'create' in request.form:
            channel_id = generate_room_code()
            active_rooms[channel_id] = {'users': 0, 'history': [], 'sids': set()}
            session['channel_id'] = channel_id
            return redirect(url_for('chat.chat'))
        elif 'join' in request.form:
            channel_id = request.form.get('channel_id')
            if channel_id in active_rooms:
                session['channel_id'] = channel_id
                return redirect(url_for('chat.chat'))
            else:
                flash('Room does not exist.', 'danger')
    
    return render_template('lobby.html')

@bp.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    channel_id = session.get('channel_id')
    if not channel_id or channel_id not in active_rooms:
        flash('Room does not exist.', 'danger')
        return redirect(url_for('chat.lobby'))

    return render_template('chat.html', username=session['username'], channel_id=channel_id)

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    room = session.get('channel_id')

    if not room:
        emit('error', {'msg': 'No room in session.'})
        return

    if room in active_rooms and active_rooms[room]['users'] >= 2:
        emit('error', {'msg': 'Room is full.'})
        return
        
    join_room(room)
    if room not in active_rooms:
        active_rooms[room] = {'users': 0, 'history': [], 'sids': set()}
    active_rooms[room]['users'] += 1
    active_rooms[room]['sids'].add(request.sid)

    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} has entered the room.\\n')
    log_file_handler.flush()
    emit('status', {'msg': f'{username} has entered the room.'}, room=room)
    emit('peer_joined', {'message': 'New peer arrived'}, room=room, include_self=False)
    emit('load_history', {'history': active_rooms[room]['history']}, to=request.sid)

@socketio.on('exchange_pubkey')
def on_exchange_pubkey(data):
    username = session.get('username')
    room = session.get('channel_id')
    if not room:
        emit('error', {'msg': 'No room in session.'})
        return
    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} sent exchange_pubkey for room {room}.\\n')
    log_file_handler.flush()
    emit('peer_pubkey', {'username': username, 'pubkey_jwk': data.get('pubkey_jwk')}, room=room, include_self=False)

@socketio.on('send_public_key')
def handle_public_key(data):
    username = session.get('username')
    room = session.get('channel_id')
    if not room:
        emit('error', {'msg': 'No room in session.'})
        return
    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} sent public key for room {room}.\\n')
    log_file_handler.flush()
    emit('receive_public_key', {'username': username, 'pubkey_jwk': data.get('pubkey_jwk')}, room=room, include_self=False)

@socketio.on('encrypted_message')
def on_encrypted_message(data):
    username = session.get('username')
    room = session.get('channel_id')
    if not room:
        emit('error', {'msg': 'No room in session.'})
        return

    payload = {
        'username': username,
        'type': data.get('type', 'text'),
        'id': data.get('id'),
        'ciphertext': data.get('ciphertext'),
        'iv': data.get('iv'),
        'timestamp': data.get('timestamp')
    }

    if room not in active_rooms:
        active_rooms[room] = {'users': 0, 'history': [], 'sids': set()}
    active_rooms[room]['history'].append(payload)

    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    ct_len = len(data.get('ciphertext') or '')
    log_file_handler.write(f'{username} sent encrypted payload ({ct_len} bytes).\\n')
    log_file_handler.flush()
    emit('encrypted_message', payload, room=room)


@socketio.on('leave')
def on_leave(data):
    username = session.get('username')
    room = session.get('channel_id')
    leave_room(room)
    if room in active_rooms:
        active_rooms[room]['users'] -= 1
        active_rooms[room]['sids'].discard(request.sid)
        if active_rooms[room]['users'] <= 0:
            del active_rooms[room]

    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} has left the room.\\n')
    log_file_handler.flush()
    emit('status', {'msg': f'{username} has left the room.'}, room=room)

@socketio.on('disconnect')
def on_disconnect():
    room = session.get('channel_id')
    username = session.get('username')
    if room in active_rooms:
        active_rooms[room]['users'] -= 1
        active_rooms[room]['sids'].discard(request.sid)
        if active_rooms[room]['users'] <= 0:
            del active_rooms[room]
    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} disconnected.\\n')
    log_file_handler.flush()

@socketio.on('destroy_room')
def destroy_room():
    room = session.get('channel_id')
    username = session.get('username')
    if room in active_rooms:
        del active_rooms[room]
        emit('room_destroyed', {'by': username}, room=room)
        log_file_handler = current_app.config['LOG_FILE_HANDLER']
        log_file_handler.write(f'{username} destroyed room {room}.\\n')
        log_file_handler.flush()
