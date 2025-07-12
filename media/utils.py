# inference_service/utils.py (Standalone with SQLite)

import os
import subprocess
import datetime
import cv2
import logging
import numpy as np
import sqlite3  # Import standard sqlite3 library
import time  # Import time for timestamps

from config import (
    FFMPEG_TIMEOUT_SECONDS, VIDEO_SAVE_FULL_PATH, SQLITE_DB_PATH,
    ALARM_TABLE_NAME, VIDEO_SAVE_DIR, VIDEO_SAVE_SUB_DIR
)

logger = logging.getLogger(__name__)

# --- SQLite Database Functions ---


def get_db_connection():
    """Creates and returns a new SQLite database connection."""
    # Use check_same_thread=False for multi-threaded access (be cautious)
    # For better thread safety, consider a connection pool or passing connections per thread/operation
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn


def initialize_database():
    """Initializes the SQLite database and creates the alarms table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Create alarms table if it doesn't exist
        # Define columns similar to the Django Alarm model but for SQLite
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {ALARM_TABLE_NAME} (
                alarm_id TEXT PRIMARY KEY,
                video_path TEXT NOT NULL,
                video_absolute_path TEXT,
                image_path TEXT,
                desc TEXT NOT NULL,
                state INTEGER DEFAULT 0,
                create_time TEXT NOT NULL
            );
        """)
        conn.commit()
        logger.info(
            f"SQLite database initialized. Table '{ALARM_TABLE_NAME}' ensured.")
    except Exception as e:
        logger.error(f"Error initializing SQLite database: {e}")
    finally:
        if conn:
            conn.close()


def insert_alarm_record(alarm_id, video_relative_path, video_absolute_path, behavior_code, alarm_data):
    """Inserts an alarm record into the SQLite database."""
    conn = None  # Initialize connection to None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        create_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sql = f"""
            INSERT INTO {ALARM_TABLE_NAME} (
                alarm_id, video_path, video_absolute_path, image_path, desc, state, create_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            alarm_id,
            video_relative_path,
            video_absolute_path,
            alarm_data.get("image_path"),
            alarm_data.get("desc", f"Behavior: {behavior_code}"),
            alarm_data.get("state", 0),
            create_time_str
        )

        # Log before execute
        logger.info(
            f"[{alarm_id}] Attempting to insert alarm record. SQL: {sql}, Params: {params}")

        cursor.execute(sql, params)
        conn.commit()
        logger.info(
            f"[{alarm_id}] Alarm record inserted into SQLite DB: {alarm_id}")
    except sqlite3.IntegrityError:
        logger.warning(
            f"[{alarm_id}] Alarm record with ID {alarm_id} already exists in DB.")
        if conn:
            conn.rollback()  # Rollback transaction on integrity error
    except Exception as e:
        # Log full exception info
        logger.error(
            f"[{alarm_id}] Error inserting alarm record into SQLite DB: {e}", exc_info=True)
        if conn:
            conn.rollback()  # Rollback transaction on any other error
    finally:
        if conn:
            conn.close()  # Ensure connection is closed


# Initialize the database when the module is imported
initialize_database()

# --- End SQLite Database Functions ---


def save_buffered_video(code, frames, fps, width, height, behavior_code, alarm_data, controls):
    """
    Saves a list of frames to a video file and creates an Alarm record using SQLite.
    Handles FFmpeg transcoding.

    Args:
        code (str): The control code associated with the video.
        frames (list): A list of numpy arrays representing video frames.
        fps (float): The frames per second for the video.
        width (int): The width of the video frames.
        height (int): The height of the video frames.
        behavior_code (str): The behavior code that triggered the save.
        alarm_data (dict): Dictionary containing data for the Alarm (e.g., 'desc', 'state').
                           This data comes from the behavior handler.
        controls (dict): Reference to the main controls dictionary to update state flags.
                         This is still needed to signal back to the VideoProcessor.
    """
    if not frames:
        logger.warning(f"[{code}] No frames in buffer to save.")
        # Reset saving flag even if no frames were saved
        if code in controls:
            controls[code]["is_saving_video"] = False
            controls[code]["save_video_thread_active"] = False
        return

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Generate a unique ID for this alarm instance
    alarm_id = f"{code}_{timestamp_str}"

    # Step 1: Generate temporary avi file path
    temp_video_filename = f"{alarm_id}_temp.avi"  # Use alarm_id in filename
    temp_video_path = os.path.join(VIDEO_SAVE_FULL_PATH, temp_video_filename)

    # Step 2: Final H.264 mp4 file path
    # Use alarm_id in filename
    final_video_filename = f"{alarm_id}_annotated.mp4"
    final_video_path = os.path.join(VIDEO_SAVE_FULL_PATH, final_video_filename)
    # Relative path for potential external access (e.g., a simple web server)
    # This relative path is relative to the base video save directory (VIDEO_SAVE_BASE_DIR)
    # Assuming VIDEO_SAVE_BASE_DIR is served statically.
    # We need to construct this relative path correctly based on the structure.
    # If VIDEO_SAVE_BASE_DIR is /app/saved_videos and VIDEO_SAVE_FULL_PATH is /app/saved_videos/alarm_videos
    # then the relative path should be saved_videos/alarm_videos/alarm_id_annotated.mp4
    VIDEO_RELATIVE_DIR = os.path.join(VIDEO_SAVE_DIR, VIDEO_SAVE_SUB_DIR)
    final_video_relative_path = os.path.join(
        VIDEO_RELATIVE_DIR, final_video_filename)

    logger.info(f"[{code}] Saving temp MJPG video to {temp_video_path}")

    # Step 3: Save as MJPG format AVI file using OpenCV
    try:
        # Use a common codec like XVID if MJPG causes issues
        # Changed to XVID for broader compatibility
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # Ensure fps is positive, default to 25 if not
        effective_fps = max(1.0, fps)
        out = cv2.VideoWriter(temp_video_path, fourcc,
                              effective_fps, (width, height))
        if not out.isOpened():
            raise IOError(f"Failed to open VideoWriter for {temp_video_path}")

        for frame in frames:
            if frame is not None:
                out.write(frame)
        out.release()
        logger.info(f"[{code}] Temp AVI video saved successfully.")
    except Exception as e:
        logger.exception(f"[{code}] Error saving temp AVI video: {e}")
        # Ensure flags are reset on error
        if code in controls:
            controls[code]["is_saving_video"] = False
            controls[code]["save_video_thread_active"] = False
        return

    # Step 4: Transcode to H.264 mp4 using FFmpeg
    try:
        logger.info(f"[{code}] Transcoding to H.264: {final_video_path}")
        ffmpeg_command = [
            'ffmpeg', '-y',  # Overwrite output file without asking
            '-i', temp_video_path,  # Input file
            '-c:v', 'libx264',  # Video codec
            # Encoding preset (balance speed and compression)
            '-preset', 'veryfast',
            # Constant Rate Factor (quality level, lower is better quality)
            '-crf', '23',
            # Pixel format (yuv420p is widely compatible)
            '-pix_fmt', 'yuv420p',
            final_video_path  # Output file
        ]
        # Execute FFmpeg command
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, timeout=FFMPEG_TIMEOUT_SECONDS)

        if result.returncode != 0:
            logger.error(
                f"[{code}] FFmpeg transcoding failed (return code {result.returncode}): {result.stderr}")
            # Ensure flags are reset on error
            if code in controls:
                controls[code]["is_saving_video"] = False
                controls[code]["save_video_thread_active"] = False
            return
        logger.info(f"[{code}] Transcoded to H.264 successfully.")
    except FileNotFoundError:
        logger.error(
            f"[{code}] FFmpeg command not found. Is FFmpeg installed and in PATH?")
        if code in controls:
            controls[code]["is_saving_video"] = False
            controls[code]["save_video_thread_active"] = False
    except subprocess.TimeoutExpired:
        logger.error(
            f"[{code}] FFmpeg transcoding timed out after {FFMPEG_TIMEOUT_SECONDS} seconds.")
        if code in controls:
            controls[code]["is_saving_video"] = False
            controls[code]["save_video_thread_active"] = False
    except Exception as e:
        logger.exception(f"[{code}] Error during FFmpeg transcoding: {e}")
        # Ensure flags are reset on error
        if code in controls:
            controls[code]["is_saving_video"] = False
            controls[code]["save_video_thread_active"] = False
        return
    finally:
        # Delete the temporary AVI file
        try:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                logger.info(
                    f"[{code}] Deleted temp AVI file: {temp_video_path}")
        except Exception as e:
            logger.warning(
                f"[{code}] Failed to delete temp AVI file {temp_video_path}: {e}")

    # Step 5: Insert Alarm data into SQLite database
    try:
        insert_alarm_record(alarm_id, final_video_relative_path,
                            final_video_path, behavior_code, alarm_data)
        logger.info(f"[{code}] Alarm data inserted into SQLite DB: {alarm_id}")
    except Exception as db_e:
        logger.error(
            f"[{code}] Error inserting Alarm data into SQLite DB: {db_e}")

    # Step 6: Mark save as complete in the control state
    if code in controls:
        controls[code]["is_saving_video"] = False
        controls[code]["save_video_thread_active"] = False
    logger.info(
        f"[{code}] Video save and Alarm DB insertion process complete.")


def build_ffmpeg_push_command(push_stream_url, width, height, input_fps):
    """
    Builds the FFmpeg command list for pushing a stream.

    Args:
        push_stream_url (str): The URL to push the stream to (rtsp:// or rtmp://).
        width (int): Frame width.
        height (int): Frame height.
        input_fps (float): Input frames per second.

    Returns:
        list: A list representing the FFmpeg command, or None if URL protocol is unsupported.
    """
    # Ensure FPS is positive, default to 25 if not
    effective_fps = max(1.0, input_fps)

    if push_stream_url.startswith("rtsp://"):
        # FFmpeg command for RTSP
        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            # Explicitly define input format from stdin
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',  # OpenCV reads as BGR
            '-s', f'{width}x{height}',
            '-r', str(effective_fps),  # Use effective input FPS for output
            '-i', '-',  # Read from stdin
            # Output stream configuration
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Ultrafast preset for minimal CPU usage
            '-tune', 'zerolatency',  # Optimize for low latency
            '-pix_fmt', 'yuv420p',  # Standard pixel format for H.264
            '-rtsp_transport', 'tcp',  # Use TCP for RTSP transport
            '-f', 'rtsp',  # Output format is RTSP
            push_stream_url  # This should be the RTSP URL of ZLMediaKit
        ]
        return command
    elif push_stream_url.startswith("rtmp://"):
        # FFmpeg command for RTMP
        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            # Explicitly define input format from stdin
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',  # OpenCV reads as BGR
            '-s', f'{width}x{height}',
            '-r', str(effective_fps),  # Use effective input FPS for output
            '-i', '-',  # Read from stdin
            # Output stream configuration
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Ultrafast preset for minimal CPU usage
            '-tune', 'zerolatency',  # Optimize for low latency
            '-pix_fmt', 'yuv420p',  # Standard pixel format for H.264
            '-f', 'flv',  # Output format is FLV for RTMP
            push_stream_url  # This should be the RTMP URL of ZLMediaKit
        ]
        return command
    else:
        return None  # Unsupported protocol
