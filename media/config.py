# inference_service/config.py (Standalone with SQLite)

import os
import logging

# Configure logging for the application
# Ensure logs are written to a file and console in a production scenario
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Application Configuration ---

# Default YOLO model path
# This should be the path to your YOLO model file (e.g., yolov8n.pt)
# YOLO模型配置 - 支持多个behavior使用不同模型
BEHAVIOR_MODEL_MAP = {
    "ZHOUJIERUQIN": "yolov8n.pt",  # 人员检测专用模型
    "RENSHUTONGJI": "yolov8s-worldv2.pt",  # 人群计数专用模型
    'INSULATOR': "insulator.pt",  # 绝缘子检测专用模型
    # 添加更多behavior和对应的模型路径
    # "NEW_BEHAVIOR": "models/yolo_new_model.pt",
}
# 为开放词汇模型配置检测类别
BEHAVIOR_CLASSES_MAP = {
    "RENSHUTONGJI": ["person"],  # 人数统计只检测人员
    # 可以为其他behavior配置特定类别
    # "VEHICLE_COUNT": ["car", "truck", "bus", "motorcycle"],
    # "ANIMAL_DETECTION": ["dog", "cat", "bird"],
}
# 默认模型路径（当behavior没有指定模型时使用）
DEFAULT_MODEL_PATH = "yolov8n.pt"

# 原有的MODEL_PATH保持向后兼容
MODEL_PATH = DEFAULT_MODEL_PATH
# MODEL_PATH = "yolov8n.pt"

# Configuration for SQLite Database
# This should be the ABSOLUTE path to your SQLite database file.
# Ensure this directory exists and the Flask app has write permissions.
# Updated to the path provided by the user. Using 'r' prefix for raw string.
SQLITE_DB_PATH = r'D:\Code\PythonCurriculum\VideoAnalyze-master\Admin\Admin.sqlite3'
# Table name for alarms in the SQLite database
# This should match the db_table name in your Django Alarm model ('av_alarm').
ALARM_TABLE_NAME = "av_alarm"


# Configuration for video saving
# This should be the ABSOLUTE path where videos are saved.
# Ensure this directory exists and the Flask app has write permissions.
# Example: VIDEO_SAVE_BASE_DIR = os.environ.get('VIDEO_SAVE_PATH', '/app/saved_videos')
# For this example, we'll use a path relative to the script's directory for simplicity,
# but an absolute path or environment variable is recommended for production.
# Note: If you want this to be relative to your Django project's MEDIA_ROOT,
# you would need a way to get that path without initializing Django fully.
# For a fully standalone Flask app, define it here explicitly.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assuming saved videos go into a 'saved_videos' subdirectory within the Flask app's directory
# If you want this relative to the Django project's media root, you'll need to adjust this
# based on the relationship between the Flask app's location and the Django project's media root.
# For now, keeping it relative to the Flask app's config file location.
VIDEO_SAVE_DIR = 'saved_videos'
VIDEO_SAVE_BASE_DIR = os.path.join(BASE_DIR, VIDEO_SAVE_DIR)

# Directory within VIDEO_SAVE_BASE_DIR where alarm videos will be saved.
VIDEO_SAVE_SUB_DIR = "alarm_videos"

# Full absolute path where alarm videos will be saved
VIDEO_SAVE_FULL_PATH = os.path.join(VIDEO_SAVE_BASE_DIR, VIDEO_SAVE_SUB_DIR)

# Duration of video to save after detection (in seconds)
VIDEO_SAVE_DURATION_SECONDS = 3

# FFmpeg command timeout (in seconds) for transcoding
FFMPEG_TIMEOUT_SECONDS = 60

# Queue sizes for inter-thread communication
FRAME_QUEUE_MAXSIZE = 60  # Increased size for raw frames (puller -> detector)
ANNOTATED_FRAME_QUEUE_MAXSIZE = 60 # Increased size for annotated frames (detector -> pusher)

# Thread join timeout (in seconds) during stopping
THREAD_JOIN_TIMEOUT_SECONDS = 10

# Stream reconnect retry delay (in seconds)
STREAM_RECONNECT_DELAY_SECONDS = 5

# Detector thread queue get timeout (in seconds)
DETECTOR_QUEUE_GET_TIMEOUT = 0.01

# Pusher thread queue get timeout (in seconds)
PUSHER_QUEUE_GET_TIMEOUT = 0.01

# Manager thread check interval (in seconds)
MANAGER_CHECK_INTERVAL_SECONDS = 0.5

# Detector FPS update interval (in seconds)
DETECTOR_FPS_UPDATE_INTERVAL = 1.0

# --- End Application Configuration ---

# Ensure necessary directories exist when this module is imported
try:
    # Ensure the directory for the SQLite DB exists
    db_dir = os.path.dirname(SQLITE_DB_PATH)
    if db_dir and not os.path.exists(db_dir):
         os.makedirs(db_dir, exist_ok=True)
         logger.info(f"Ensured SQLite DB directory exists: {db_dir}")

    # Ensure the video save directory exists
    os.makedirs(VIDEO_SAVE_FULL_PATH, exist_ok=True)
    logger.info(f"Ensured video save directory exists: {VIDEO_SAVE_FULL_PATH}")

except Exception as e:
    logger.error(f"Failed to create necessary directories: {e}")
    # Handle this critical error appropriately in a real application


logger.info("Configuration loaded.")
