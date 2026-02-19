import uuid
import string
import random
from flask import Blueprint, render_template, session, redirect, url_for, current_app, flash, request
from app import socketio
from flask_socketio import emit, join_room, leave_room

bp = Blueprint('chat', __name__)

rooms = {}

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
            rooms[channel_id] = {'users': 0}
            return redirect(url_for('chat.chat', channel_id=channel_id))
        elif 'join' in request.form:
            channel_id = request.form.get('channel_id')
            if channel_id in rooms:
                return redirect(url_for('chat.chat', channel_id=channel_id))
            else:
                flash('Room does not exist.', 'danger')
    
    return render_template('lobby.html')

@bp.route('/chat/<channel_id>')
def chat(channel_id):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    if channel_id not in rooms:
        flash('Room does not exist.', 'danger')
        return redirect(url_for('chat.lobby'))

    return render_template('chat.html', username=session['username'], channel_id=channel_id)

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    room = data['room']

    if room in rooms and rooms[room]['users'] >= 2:
        emit('error', {'msg': 'Room is full.'})
        return
        
    join_room(room)
    if room not in rooms:
        rooms[room] = {'users': 0}
    rooms[room]['users'] += 1

    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} has entered the room.\\n')
    log_file_handler.flush()
    emit('status', {'msg': f'{username} has entered the room.'}, room=room)

@socketio.on('message')
def on_message(data):
    username = session.get('username')
    room = data['room']
    message = data['message']
    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username}: {message}\\n')
    log_file_handler.flush()
    emit('message', {'username': username, 'msg': message}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = session.get('username')
    room = data['room']
    leave_room(room)
    if room in rooms:
        rooms[room]['users'] -= 1
        if rooms[room]['users'] == 0:
            del rooms[room]

    log_file_handler = current_app.config['LOG_FILE_HANDLER']
    log_file_handler.write(f'{username} has left the room.\\n')
    log_file_handler.flush()
    emit('status', {'msg': f'{username} has left the room.'}, room=room)
