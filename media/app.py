# inference_service/app.py (Standalone with SQLite)

from flask import Flask, request, jsonify
import logging
import os
import sys
import time # Import standard time

# Import configuration and VideoProcessor
import config
from video_processor import VideoProcessor
# Note: No Django imports here anymore

# Configure logging (basic configuration is in config.py, but can add more here)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize processor with model path from config
video_processor = VideoProcessor()

# --- API Endpoints Aligned with Analyzer Class ---

@app.route('/api/controls', methods=['POST'])  # Analyzer uses POST /api/controls
def get_controls_route_aligned():
    """
    API endpoint to get the status of all active control instances.
    """
    # Analyzer expects {"code": 1000, "msg": "...", "data": [...]}
    controls_list = video_processor.get_all_controls()
    return jsonify({
        "code": 1000,
        "msg": "success",
        "data": controls_list
    })


@app.route('/api/control', methods=['POST'])  # Analyzer uses POST /api/control
def get_control_route_aligned():
    """
    API endpoint to get the status of a specific control instance by code.
    """
    data = request.json
    code = data.get('code')

    if not code:
        return jsonify({
            "code": 400,  # Using a non-1000 code for error
            "msg": "Missing code parameter",
            "control": {}  # Return empty control on error
        }), 400

    # Flask's get_status returns the status dictionary directly
    status_data = video_processor.get_status(code)

    # Analyzer expects {"code": 1000, "msg": "...", "control": {...}}
    # If get_status indicates not found or inactive, adjust response code
    if status_data.get("status") == "inactive" and status_data.get("error") == "Control not found or inactive":
        return jsonify({
            "code": 404,  # Using 404 for not found
            "msg": status_data.get("error"),
            "control": {}
        }), 404
    else:
        return jsonify({
            "code": 1000,
            "msg": "success",
            "control": status_data  # Return the status dictionary as 'control'
        })


@app.route('/api/control/add', methods=['POST'])  # Analyzer uses POST /api/control/add
def start_detection_route_aligned():
    """
    API endpoint to start a new detection control instance.
    """
    data = request.json
    # Analyzer sends these parameter names
    code = data.get('code')
    behaviorCode = data.get('behaviorCode')
    streamUrl = data.get('streamUrl')
    pushStream = data.get('pushStream', False) # Default to False if not provided
    pushStreamUrl = data.get('pushStreamUrl')

    if not all([code, behaviorCode, streamUrl]):
        return jsonify({
            "code": 400,
            "msg": "Missing required parameters (code, behaviorCode, streamUrl)"
        }), 400

    if pushStream and not pushStreamUrl:
        return jsonify({
            "code": 400,
            "msg": "pushStream is true but pushStreamUrl is missing"
        }), 400

    # Call the internal start_detection method with the parameters
    success, message = video_processor.start_detection(
        code, behaviorCode, streamUrl, pushStream, pushStreamUrl
    )

    # Analyzer expects {"code": 1000, "msg": "..."} on success
    if success:
        return jsonify({
            "code": 1000,
            "msg": message
        })
    else:
        # Use a specific error code if the model failed to load or behavior is unsupported
        error_code = 500 # Default internal server error
        if "YOLO model failed to load" in message:
            error_code = 503 # Service Unavailable
        elif "Unsupported behavior code" in message:
             error_code = 400 # Bad Request (invalid input)
        elif "Detection already running" in message:
             error_code = 409 # Conflict

        return jsonify({
            "code": error_code,
            "msg": message
        }), error_code


@app.route('/api/control/cancel', methods=['POST'])  # Analyzer uses POST /api/control/cancel
def stop_detection_route_aligned():
    """
    API endpoint to stop a detection control instance by code.
    """
    data = request.json
    code = data.get('code')  # Analyzer sends 'code'

    if not code:
        return jsonify({
            "code": 400,
            "msg": "Missing code parameter"
        }), 400

    # Call the internal stop_detection method
    success, message = video_processor.stop_detection(code)

    # Analyzer expects {"code": 1000, "msg": "..."} on success
    if success:
        return jsonify({
            "code": 1000,
            "msg": message
        })
    else:
        # If stop fails, it might be because the control wasn't found initially
        error_code = 500 # Default internal server error
        if "No detection found" in message:
            error_code = 404 # Not Found
        elif "Failed to stop detection gracefully" in message:
            error_code = 500 # Still an internal issue

        return jsonify({
            "code": error_code,
            "msg": message
        }), error_code


# Keeping the original health check route
@app.route('/health', methods=['GET'])
def health_check_route():
    """
    Health check endpoint to monitor the application status.
    Reports the number of actively running detection pipelines.
    """
    # Count controls where the manager thread is still alive and not explicitly stopping/errored
    active_count = sum(1 for control in video_processor.controls.values()
                       if control["manager_thread"].is_alive()
                       and not control["stop_event"].is_set()
                       and not control["error_event"].is_set())
    # Since Django is removed, we don't report django_ready
    return jsonify({"status": "ok", "active_detections": active_count})


if __name__ == "__main__":
    # This block is for running the Flask app directly for development or testing.
    # For production, consider using a production WSGI server like Gunicorn or uWSGI.
    # Example Gunicorn command: gunicorn -w 4 -b 0.0.0.0:9002 inference_service.app:app
    print("Starting Flask app on 0.0.0.0:9002")
    # Using threaded=True for development server; a production WSGI server is recommended
    # debug=True should only be used in development
    app.run(host="0.0.0.0", port=9002, debug=False, threaded=True)

