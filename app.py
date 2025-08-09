# app.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from uuid import uuid4
import os

# --- Configuration ---
# Use a secret key for Flask sessions.
# In a production environment, this should be a random, complex string.
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')
socketio = SocketIO(app)

# --- Anonymity Rationale ---
# Instead of a traditional JWT with user data, we use a simple, temporary UUID
# as an anonymous session ID. This allows the server to differentiate between
# active connections without storing any personally identifiable information.
# This dictionary maps session IDs to the current list of connected users.
# The `request.sid` is the unique session ID provided by Flask-SocketIO.
active_sessions = {}
session_counter = 0

# --- Routes ---
@app.route('/')
def index():
    """
    Main route for the chat application.
    Serves the HTML frontend.
    """
    return render_template('index.html')

# --- WebSocket Event Handlers ---
@socketio.on('connect')
def handle_connect():
    """
    Handles a new client connection.
    Assigns a unique, anonymous session ID and adds the user to the 'broadcast' room.
    """
    global session_counter
    # The `request.sid` is a unique identifier for the session provided by SocketIO.
    # We will use this as our anonymous 'token'.
    session_id = request.sid
    # This counter gives a simple, human-readable anonymous name.
    session_counter += 1
    anonymous_name = f"Anonymous_{session_counter}"
    active_sessions[session_id] = anonymous_name

    # Log connection for debugging, but note that a production server
    # should NOT log the IP address or any other identifying data.
    print(f"Client connected with SID: {session_id}, assigned name: {anonymous_name}")

    # Join a common room for all users to broadcast messages.
    join_room('broadcast')

    # Emit a system message to all clients in the 'broadcast' room.
    # Note that we do not broadcast the 'who' of the connection, only that a user joined.
    emit('status', {'msg': f"A new user has joined the chat."}, room='broadcast')


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handles a client disconnection.
    Removes the anonymous session ID and notifies the room.
    """
    session_id = request.sid
    if session_id in active_sessions:
        # Get the anonymous name before removing the session
        anonymous_name = active_sessions.pop(session_id)
        print(f"Client disconnected with SID: {session_id}, was: {anonymous_name}")

        # Emit a system message to all clients in the 'broadcast' room.
        emit('status', {'msg': "An anonymous user has left the chat."}, room='broadcast')


@socketio.on('message')
def handle_message(data):
    """
    Handles an incoming message from a client.
    Broadcasts the message to all other clients in the 'broadcast' room.
    """
    session_id = request.sid
    if session_id in active_sessions:
        # Get the anonymous name for this session.
        anonymous_name = active_sessions[session_id]
        message_text = data.get('msg')
        
        print(f"Received message from {anonymous_name} ({session_id}): {message_text}")
        
        # Emit the message to everyone in the 'broadcast' room.
        # We include the anonymous name to distinguish senders.
        # This name is temporary and not linked to any real-world identity.
        emit('message', {
            'sender': anonymous_name, 
            'msg': message_text
        }, room='broadcast')


if __name__ == '__main__':
    # The `port` is set to 5000 for local development.
    # In a production environment, you would use a web server like Gunicorn.
    socketio.run(app, debug=True, port=5000)