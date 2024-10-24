# app.py

import os
import io
import time
from typing import Optional, Dict, Any
import logging
import traceback
from datetime import datetime, timezone
import sys

import json_log_formatter
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from PIL import Image
import numpy as np  # For make_serializable function

from src.parsers.parser_options import ParserOption
from src.parsers.parser_registry import ParserRegistry
from src.utils.config_loader import ConfigLoader
from src.utils.config import Config

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize JSON formatter for structured logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler()
json_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(json_handler)
logger.setLevel(Config.get_log_level())

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


def make_serializable(obj):
    """
    Recursively converts non-serializable objects to serializable types.

    Args:
        obj: The object to convert.

    Returns:
        A JSON-serializable version of the object.
    """
    if isinstance(obj, np.float32):
        logger.debug("Converting np.float32 to float.")
        return float(obj)
    elif isinstance(obj, np.float64):
        logger.debug("Converting np.float64 to float.")
        return float(obj)
    elif isinstance(obj, np.int32):
        logger.debug("Converting np.int32 to int.")
        return int(obj)
    elif isinstance(obj, np.int64):
        logger.debug("Converting np.int64 to int.")
        return int(obj)
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(element) for element in obj]
    elif isinstance(obj, tuple):
        return tuple(make_serializable(element) for element in obj)
    elif isinstance(obj, set):
        return [make_serializable(element) for element in obj]
    elif isinstance(obj, float):
        return obj
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, str):
        return obj
    else:
        logger.warning("Encountered non-serializable type: %s. Converting to string.", type(obj))
        return str(obj)


def background_parse(sid, parser, email_content, document_image):
    """Perform email parsing and emit progress updates to the client."""
    try:
        with parser as p:
            if not p.health_check():
                socketio.emit('parsing_error', {'error': 'Parser health check failed.'}, room=sid)
                return

            socketio.emit('parsing_started', {'message': 'Parsing started...'}, room=sid)

            # Progress updates tied to actual parsing stages
            stages = [
                {'stage': 'Initializing parser', 'progress': 10},
                {'stage': 'Processing email content', 'progress': 30},
                {'stage': 'Extracting entities', 'progress': 50},
                {'stage': 'Finalizing results', 'progress': 80},
                {'stage': 'Completed', 'progress': 100},
            ]

            for step in stages:
                socketio.emit('parsing_progress', {'stage': step['stage'], 'progress': step['progress']}, room=sid)
                socketio.sleep(1)  # Use socketio.sleep instead of time.sleep

            # Actual parsing
            result = p.parse_email(email_content=email_content, document_image=document_image)

            # Add formatted output to response if available
            if 'email_metadata' in result:
                formatted_text = format_schema_output(result['email_metadata'])
                result['formatted_schema'] = formatted_text

            # Convert the result to a serializable format
            serializable_result = make_serializable(result)
            logger.debug("Serialized Result: %s", serializable_result)

            socketio.emit('parsing_completed', {'result': serializable_result}, room=sid)

    except Exception as e:
        logger.error("Parsing failed: %s", e, exc_info=True)
        error_info = {
            'taskName': None,
            'message': f"Parsing failed: {str(e)}",
            'time': datetime.now(timezone.utc).isoformat(),
            'exc_info': traceback.format_exc()
        }
        serializable_error = make_serializable(error_info)
        socketio.emit('parsing_error', {'error': serializable_error}, room=sid)


@app.route("/", methods=["GET"])
def index():
    """Render the index page."""
    logger.info("Rendering index page.")
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    """Serve the favicon.ico file."""
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
    """Handle the email parsing request."""
    # Removed print statements for cleaner production code
    email_content = request.form.get("email_content", "").strip()
    image_file = request.files.get("document_image")
    parser_option_str = request.form.get("parser_option", "").strip()
    socket_id = request.form.get('socket_id')

    # Validation
    if not email_content and not image_file:
        return jsonify({"error_message": "Please provide email content or document image"}), 400

    if not parser_option_str:
        return jsonify({"error_message": "Please select a parser option."}), 400

    # Retrieve socket ID from form data instead of headers
    sid = socket_id
    if not sid:
        return jsonify({"error_message": "Socket ID not provided."}), 400

    logger.info("Received Socket ID: %s", sid)

    # Convert parser_option_str to ParserOption Enum
    try:
        parser_option = ParserOption(parser_option_str)
    except ValueError:
        return jsonify({"error_message": f"Invalid parser option: {parser_option_str}"}), 400

    try:
        parser = ParserRegistry.get_parser(parser_option, socketio, sid)
    except Exception as e:
        logger.error("Failed to initialize parser: %s", e)
        return jsonify({"error_message": "Parser initialization failed"}), 500

    if parser is None:
        return jsonify({"error_message": "Parser could not be initialized"}), 500

    # Process image if provided
    document_image = None
    if image_file:
        try:
            document_image = Image.open(io.BytesIO(image_file.read()))
        except Exception as e:
            logger.error("Image processing failed: %s", e)
            return jsonify({"error_message": "Invalid image format"}), 400

    # Start parsing in background
    socketio.start_background_task(background_parse, sid, parser, email_content, document_image)

    return jsonify({"message": "Parsing started"}), 202


@app.route("/health", methods=["GET"])
def health_check():
    """Perform health checks on parsers."""
    try:
        status = ParserRegistry.health_check()
        return jsonify({"status": "healthy", "parsers": status}), 200
    except Exception as e:
        logger.error("Health check failed: %s", e, exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle new client connections."""
    sid = request.sid
    logger.info("Client connected: %s", sid)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnections."""
    sid = request.sid
    logger.info("Client disconnected: %s", sid)


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions."""
    logger.error("Unhandled exception: %s", e, exc_info=True)
    return jsonify({"error_message": "An internal error occurred."}), 500


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    logger.warning("404 error: %s not found. Exception: %s", request.url, e)
    return jsonify({"error_message": "The requested URL was not found on the server."}), 404


if __name__ == "__main__":
    try:
        # Load configuration
        config = ConfigLoader.load()

        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "5000"))

        static_dir = os.path.join(app.root_path, "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
            logger.info("Created 'static' directory at %s", static_dir)

        # Initialize parsers
        ParserRegistry.initialize_parsers(config)

        socketio.run(app, host=host, port=port, debug=True, use_reloader=False)
    except Exception as e:
        logger.critical("Failed to start the Flask application: %s", e, exc_info=True)
        # Perform any necessary cleanup
        ParserRegistry.cleanup_parsers()
        # Exit with a non-zero status code
        sys.exit(1)
