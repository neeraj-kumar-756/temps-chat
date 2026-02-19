from gevent import monkey
monkey.patch_all()

from app import create_app, socketio
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

app = create_app()

if __name__ == '__main__':
    app.debug = True  # Enable debug directly on the Flask app instead
    server = WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    print("Server started. Press Ctrl+C to quit.")
    server.serve_forever()
