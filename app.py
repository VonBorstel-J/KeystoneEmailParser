# app.py

import os
import logging
import json_log_formatter
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from src.parsers.parser_options import ParserOption
from src.parsers.parser_registry import ParserRegistry
from dotenv import load_dotenv
from PIL import Image
import io
from threading import Thread
import time
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize JSON formatter for structured logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler()
json_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(json_handler)
logger.setLevel(logging.DEBUG)

socketio = SocketIO(app, cors_allowed_origins="*")

def format_schema_output(formatted_data: Dict[str, Any]) -> str:
    """Formats the validated data back into the schema template format."""
    output = []
    for section, fields in formatted_data.items():
        output.append(section)
        output.append('')
        for field, value in fields.items():
            output.append(f"{field}: {value}")
        output.append('')
    return '\n'.join(output)

def background_parse(sid, parser, email_content, document_image):
    """Perform email parsing and emit progress updates to the client."""
    try:
        with parser as p:
            if not p.health_check():
                socketio.emit('parsing_error', {'error': 'Parser health check failed.'}, room=sid)
                return

            socketio.emit('parsing_started', {'message': 'Parsing started...'}, room=sid)

            # Progress updates (These can be tied to actual parsing stages if desired)
            steps = [
                {'stage': 'Initializing parser', 'progress': 10},
                {'stage': 'Processing email content', 'progress': 30},
                {'stage': 'Extracting entities', 'progress': 50},
                {'stage': 'Finalizing results', 'progress': 80},
                {'stage': 'Completed', 'progress': 100},
            ]

            for step in steps:
                socketio.emit('parsing_progress', {'stage': step['stage'], 'progress': step['progress']}, room=sid)
                time.sleep(1)  # Simulate progress. Replace with actual parsing progress.

            # Actual parsing
            result = p.parse_email(email_content=email_content, document_image=document_image)

            # Add formatted output to response
            if 'formatted_output' in result:
                formatted_text = format_schema_output(result['formatted_output'])
                result['formatted_schema'] = formatted_text

            socketio.emit('parsing_completed', {'result': result}, room=sid)

    except Exception as e:
        logger.error(f"Parsing failed: {e}", exc_info=True)
        socketio.emit('parsing_error', {'error': str(e)}, room=sid)

@app.route("/", methods=["GET"])
def index():
    logger.info("Rendering index page.")
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    favicon_path = os.path.join(app.root_path, "static", "favicon.ico")
    if os.path.exists(favicon_path):
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )
    return jsonify({"error_message": "favicon.ico not found."}), 404

@app.route("/parse_email", methods=["POST"])
def parse_email_route():
    email_content = request.form.get("email_content", "").strip()
    image_file = request.files.get("document_image")
    parser_option = request.form.get("parser_option", "").strip()

    # Validation
    if not email_content and not image_file:
        return jsonify({"error_message": "Please provide email content or document image"}), 400

    if not parser_option:
        return jsonify({"error_message": "Please select a parser option."}), 400

    sid = request.headers.get('X-Socket-ID')
    if not sid:
        return jsonify({"error_message": "Socket ID not provided."}), 400

    try:
        parser = ParserRegistry.get_parser(ParserOption.ENHANCED_PARSER)
    except Exception as e:
        logger.error(f"Failed to initialize parser: {e}")
        return jsonify({"error_message": "Parser initialization failed"}), 500

    # Process image if provided
    document_image = None
    if image_file:
        try:
            document_image = Image.open(io.BytesIO(image_file.read()))
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return jsonify({"error_message": "Invalid image format"}), 400

    # Start parsing in background
    thread = Thread(target=background_parse, args=(sid, parser, email_content, document_image))
    thread.start()

    return jsonify({"message": "Parsing started"}), 202

@app.route("/health", methods=["GET"])
def health_check():
    try:
        status = ParserRegistry.health_check()
        return jsonify({"status": "healthy", "parsers": status}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    logger.info(f"Client connected: {sid}")
    emit('connected', {'sid': sid})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    logger.info(f"Client disconnected: {sid}")

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"error_message": "An internal error occurred."}), 500

@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 error: {request.url} not found.")
    return jsonify({"error_message": "The requested URL was not found on the server."}), 404

if __name__ == "__main__":
    try:
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", 5000))

        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
            logger.info(f"Created 'static' directory at {static_dir}")

        socketio.run(app, host=host, port=port, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start the Flask application: {e}", exc_info=True)
        raise e
