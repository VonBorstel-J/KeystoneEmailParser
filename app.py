# src/app.py
import eventlet
eventlet.monkey_patch()
import os
import io
import sys
import torch
import signal
import logging
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import json_log_formatter
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS  # CORS support added
from flask_socketio import SocketIO
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import asyncio

from src.parsers.enhanced_parser import EnhancedParser
from src.parsers.parser_options import ParserOption
from src.parsers.parser_registry import ParserRegistry
from src.utils.config import Config
from src.utils.exceptions import InitializationError

# Set memory fraction to 90% of total GPU memory
if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(0.9)
    # Clear the FFT plan cache for potentially faster CUDA operations
    torch.backends.cuda.cufft_plan_cache.clear()

def setup_logging() -> logging.Logger:
    formatter = json_log_formatter.JSONFormatter()
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger = logging.getLogger("AppLogger")
    logger.addHandler(json_handler)
    logger.setLevel(logging.DEBUG)
    return logger

def init_app() -> (Flask, SocketIO):
    load_dotenv()
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # Configure CORS properly
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/socket.io/*": {"origins": "*"}
    })
    
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        logger=True,
        engineio_logger=True,
        async_mode="eventlet",
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=100 * 1024 * 1024,  # 100MB for large files
        transport='websocket'
    )
    
    return app, socketio

def setup_cache_dirs(logger: logging.Logger):
    cache_dir = str(Path("D:/AiHub"))
    os.environ["HF_HOME"] = cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    logger.info("Cache directory set to: %s", cache_dir)

    if torch.cuda.is_available():
        logger.info("CUDA available: %s", torch.cuda.get_device_name(0))
    else:
        logger.info("CUDA not available, using CPU")

logger = setup_logging()
app, socketio = init_app()

def format_schema_output(formatted_data: Dict[str, Any]) -> str:
    output = []
    for section, fields in formatted_data.items():
        output.append(section)
        output.append("")
        for field, value in fields.items():
            output.append(f"{field}: {value}")
        output.append("")
    return "\n".join(output)

def make_serializable(obj: Any) -> Any:
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(element) for element in obj]
    elif isinstance(obj, tuple):
        return tuple(make_serializable(element) for element in obj)
    elif isinstance(obj, set):
        return [make_serializable(element) for element in obj]
    elif isinstance(obj, (float, int, str)):
        return obj
    else:
        return str(obj)

def background_parse(
    sid: str,
    parser_option: str,
    email_content: str,
    document_image: Optional[Image.Image],
):
    # Create event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        input_type = None
        if email_content and document_image:
            input_type = 'both'
        elif email_content:
            input_type = 'text'
        elif document_image:
            input_type = 'image'

        parser = ParserRegistry.get_parser(
            parser_option=ParserOption(parser_option),
            socketio=socketio,
            sid=sid,
        )
        if parser is None:
            socketio.emit(
                "parsing_error", {"error": f"Parser for option {parser_option} not found."}, room=sid
            )
            return

        with parser:
            if not parser.is_initialized:
                parser.initialize(input_type=input_type)
            if not parser.health_check():
                socketio.emit(
                    "parsing_error", {"error": "Parser health check failed."}, room=sid
                )
                return

            socketio.emit(
                "parsing_started", {"message": "Parsing started..."}, room=sid
            )

            stages = [
                {"stage": "Initializing parser", "progress": 10},
                {"stage": "Processing email content", "progress": 30},
                {"stage": "Extracting entities", "progress": 50},
                {"stage": "Finalizing results", "progress": 80},
                {"stage": "Completed", "progress": 100},
            ]

            for step in stages:
                socketio.emit(
                    "parsing_progress",
                    {"stage": step["stage"], "progress": step["progress"]},
                    room=sid,
                )
                socketio.sleep(1)

            result = parser.parse_email(
                email_content=email_content, document_image=document_image
            )

            # Handle structured_data and metadata
            structured_data = result.get("structured_data", {})
            metadata = result.get("metadata", {})

            # Optionally, log or use metadata
            logger.debug("Metadata from parsing: %s", metadata)

            if "email_metadata" in structured_data:
                formatted_text = format_schema_output(structured_data["email_metadata"])
                structured_data["formatted_schema"] = formatted_text

            serializable_result = make_serializable(structured_data)
            logger.debug("Serialized Result: %s", serializable_result)

            socketio.emit(
                "parsing_completed", {"result": serializable_result}, room=sid
            )

    except Exception as e:
        logger.error("Error during parsing: %s", e, exc_info=True)
        error_info = {
            "type": "unexpected_error",
            "message": f"An unexpected error occurred: {str(e)}",
            "time": datetime.now(timezone.utc).isoformat(),
            "exc_info": traceback.format_exc(),
        }
        serializable_error = make_serializable(error_info)
        socketio.emit("parsing_error", {"error": serializable_error}, room=sid)
    finally:
        loop.close()

# Frontend route
@app.route("/", methods=["GET"])
def index():
    logger.info("Rendering index page.")
    return render_template("index.html")

# Favicon route
@app.route("/favicon.ico")
def favicon_route():
    favicon_path = os.path.join(app.root_path, "static", "favicon.ico")
    if os.path.exists(favicon_path):
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )
    logger.warning("favicon.ico not found at path: %s", favicon_path)
    return jsonify({"error_message": "favicon.ico not found."}), 404

# API routes - all prefixed with /api
@app.route("/api/parse_email", methods=["POST"])
def parse_email_route():
    try:
        email_content = request.form.get("email_content", "").strip()
        image_file = request.files.get("document_image")
        parser_option_str = request.form.get("parser_option", "").strip()
        socket_id = request.form.get("socket_id")

        if not socket_id:
            logger.warning("No socket ID provided.")
            return jsonify({"error_message": "Socket ID not provided."}), 400

        # Validate inputs
        if not email_content and not image_file:
            logger.warning("No email content or document image provided.")
            return jsonify(
                {"error_message": "Please provide email content or document image"}
            ), 400

        # Start parsing in background task
        socketio.start_background_task(
            background_parse, 
            socket_id,
            parser_option_str, 
            email_content,
            image_file.read() if image_file else None
        )

        return jsonify({"message": "Parsing started", "socket_id": socket_id}), 202

    except Exception as e:
        logger.error(f"Error in parse_email_route: {str(e)}", exc_info=True)
        return jsonify({"error_message": "Internal server error"}), 500

@app.route("/api/health", methods=["GET"])
def health_check_route():
    try:
        status = ParserRegistry.health_check()
        logger.info("Health check passed.")
        return jsonify({"status": "healthy", "parsers": status}), 200
    except Exception as e:
        logger.error("Health check failed: %s", e, exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.warning("404 error: %s not found. Exception: %s", request.url, error)
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error("Internal server error: %s", error, exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(e: Exception):
    logger.error("Unhandled exception: %s", e, exc_info=True)
    return jsonify({"error_message": "An internal error occurred."}), 500

@app.errorhandler(404)
def page_not_found(e: Exception):
    logger.warning("404 error: %s not found. Exception: %s", request.url, e)
    return (
        jsonify({"error_message": "The requested URL was not found on the server."}),
        404,
    )

# SocketIO event handlers
@socketio.on("connect")
def handle_connect():
    sid = request.sid
    logger.info("Client connected: %s", sid)
    logger.debug("Connection headers: %s", request.headers)
    logger.debug("Connection environment: %s", request.environ)
    
    # Emit a test message to verify connection
    try:
        socketio.emit("connection_test", {"status": "connected", "sid": sid}, room=sid)
        logger.debug("Sent connection test to client %s", sid)
    except Exception as e:
        logger.error("Failed to emit connection test: %s", e, exc_info=True)

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    logger.info("Client disconnected: %s", sid)
    logger.debug("Disconnect reason: %s", request.environ.get('disconnection_reason', 'unknown'))

@socketio.on_error()
def error_handler(e):
    logger.error("SocketIO error: %s", e, exc_info=True)
    if request.sid:
        socketio.emit(
            "parsing_error",
            {"error": "An unexpected error occurred during socket communication"},
            room=request.sid
        )

def signal_handler(_sig, _frame):
    try:
        logger.info("Shutdown initiated...")
        ParserRegistry.cleanup_parsers()
        logger.info("Cleanup completed successfully.")
    except Exception as e:
        logger.error("Error during cleanup: %s", e, exc_info=True)
    finally:
        sys.exit(0)

if __name__ == "__main__":
    try:
        logger.info("Starting application initialization...")

        setup_cache_dirs(logger)

        logger.info("Loading configuration...")
        Config.initialize()
        logger.info("Configuration loaded successfully")

        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "5000"))
        logger.info("Server will start on %s:%d", host, port)

        static_dir = os.path.join(app.root_path, "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
            logger.info("Created static directory at %s", static_dir)

        ParserRegistry.initialize_parsers()
        logger.info("Parsers initialized successfully")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        socketio.run(app, host=host, port=port, debug=True, use_reloader=False)
    except InitializationError as ie:
        logger.critical(
            "Parser initialization failed during startup: %s", ie, exc_info=True
        )
        try:
            ParserRegistry.cleanup_parsers()
        except Exception as cleanup_e:
            logger.error(
                "Error during cleanup after failed startup: %s",
                cleanup_e,
                exc_info=True,
            )
        sys.exit(1)
    except Exception as e:
        logger.critical("Failed to start the Flask application: %s", e, exc_info=True)
        try:
            ParserRegistry.cleanup_parsers()
        except Exception as cleanup_e:
            logger.error(
                "Error during cleanup after failed startup: %s",
                cleanup_e,
                exc_info=True,
            )
        sys.exit(1)
