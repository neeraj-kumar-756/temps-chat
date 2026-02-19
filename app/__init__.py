import os
import atexit
import uuid
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
socketio = SocketIO()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_mapping(
        SECRET_KEY=os.urandom(24),
        SQLALCHEMY_DATABASE_URI='sqlite:///../instance/db.sqlite3',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    socketio.init_app(app, async_mode='gevent')

    from .routes import auth, chat
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp)

    # Ephemeral logging
    LOG_FILE = os.path.join(app.instance_path, f'chat_log_{uuid.uuid4()}.log')
    log_file_handler = open(LOG_FILE, 'a')
    app.config['LOG_FILE_HANDLER'] = log_file_handler

    def delete_log():
        log_file_handler.close()
        os.remove(LOG_FILE)

    atexit.register(delete_log)
    
    with app.app_context():
        db.create_all()

    return app
