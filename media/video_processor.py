# inference_service/video_processor.py (Standalone with SQLite)

import threading
import time
import logging
import queue
import subprocess
import numpy as np
import cv2
from ultralytics import YOLO
import collections
import os
import datetime # Import standard datetime

from config import (
    BEHAVIOR_MODEL_MAP, BEHAVIOR_CLASSES_MAP, DEFAULT_MODEL_PATH, VIDEO_SAVE_DURATION_SECONDS, 
    FRAME_QUEUE_MAXSIZE, ANNOTATED_FRAME_QUEUE_MAXSIZE, THREAD_JOIN_TIMEOUT_SECONDS,
    STREAM_RECONNECT_DELAY_SECONDS, DETECTOR_QUEUE_GET_TIMEOUT,
    PUSHER_QUEUE_GET_TIMEOUT, MANAGER_CHECK_INTERVAL_SECONDS,
    DETECTOR_FPS_UPDATE_INTERVAL
)
# Import utility functions (which now use sqlite3)
from utils import save_buffered_video, build_ffmpeg_push_command
# Import the function to get behavior handlers
from behaviors import get_behavior_handler

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Manages video stream processing pipelines for multiple control codes.
    Handles stream pulling, object detection, behavior delegation,
    and optional stream pushing. Saves Alarm data to SQLite.
    """
    def __init__(self):
        """
        Initializes the VideoProcessor.
        不再预加载单一模型，而是根据需要动态加载不同的模型
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("VideoProcessor initializing...")
        
        # 存储已加载的模型，避免重复加载
        self.loaded_models = {}
        
        # Dictionary to hold control objects for each stream
        self.controls = {}
        logger.info("VideoProcessor initialized.")

    def _get_model_for_behavior(self, behavior_code):
        """
        根据behavior_code获取对应的YOLO模型，并设置检测类别
        
        Args:
            behavior_code (str): 行为代码
            
        Returns:
            YOLO: 对应的YOLO模型实例，如果加载失败返回None
        """
        # 确定使用哪个模型路径
        model_path = BEHAVIOR_MODEL_MAP.get(behavior_code, DEFAULT_MODEL_PATH)
        
        # 创建包含类别信息的缓存key
        classes = BEHAVIOR_CLASSES_MAP.get(behavior_code)
        cache_key = f"{model_path}_{str(classes)}" if classes else model_path
        
        # 如果模型已经加载过，直接返回
        if cache_key in self.loaded_models:
            self.logger.info(f"Using cached model for behavior {behavior_code}: {model_path}")
            return self.loaded_models[cache_key]
        
        # 加载新模型
        try:
            self.logger.info(f"Loading YOLO model for behavior {behavior_code}: {model_path}")
            model = YOLO(model_path)
            
            # 如果该behavior配置了特定类别，设置模型检测类别
            if classes:
                self.logger.info(f"Setting model classes for behavior {behavior_code}: {classes}")
                try:
                    model.set_classes(classes)
                    self.logger.info(f"Successfully set model classes: {classes}")
                except Exception as e:
                    self.logger.warning(f"Failed to set classes for model {model_path}: {e}")
                    self.logger.warning("Model will use default classes")
            
            self.loaded_models[cache_key] = model
            self.logger.info(f"YOLO model loaded successfully for behavior {behavior_code}")
            return model
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model for behavior {behavior_code} from {model_path}: {e}")
            return None

    def start_detection(self, code, behavior_code, stream_url, push_stream=False, push_stream_url=None):
        """
        Start detection on a video stream with a threaded pipeline.
        """
        if code in self.controls and self.controls[code]["manager_thread"].is_alive():
            return False, f"Detection already running for code: {code}"

        # 验证behavior并获取对应模型
        model = self._get_model_for_behavior(behavior_code)
        if model is None:
            return False, f"Failed to load YOLO model for behavior: {behavior_code}"

        # Validate behavior code by attempting to get a handler
        if get_behavior_handler(behavior_code, code) is None:
             return False, f"Unsupported behavior code: {behavior_code}"

        logger.info(f"[{code}] Attempting to start detection for stream: {stream_url} with behavior: {behavior_code}")

        # ...existing code for creating queues and events...
        frame_queue = queue.Queue(maxsize=FRAME_QUEUE_MAXSIZE)
        annotated_frame_queue = queue.Queue(maxsize=ANNOTATED_FRAME_QUEUE_MAXSIZE)
        stop_event = threading.Event()
        error_event = threading.Event()

        # Initialize control with behavior-specific model
        self.controls[code] = {
            "behavior_code": behavior_code,
            "model": model,  # 为每个control分配特定的模型
            "stream_url": stream_url,
            "push_stream": push_stream,
            "push_stream_url": push_stream_url,
            "frame_queue": frame_queue,
            "annotated_frame_queue": annotated_frame_queue,
            "stop_event": stop_event,
            "error_event": error_event,
            "fps": 0.0,
            "start_time": time.time(),
            "frames_processed": 0,
            "status": "starting",
            "error": None,
            "manager_thread": None,
            "puller_thread": None,
            "detector_thread": None,
            "pusher_thread": None,
            "width": 0,
            "height": 0,
            "input_fps": 0.0,
            "frame_buffer": collections.deque(maxlen=1),
            "is_saving_video": False,
            "save_video_thread_active": False
        }

        # ...existing code for starting manager thread...
        manager_thread = threading.Thread(
            target=self._manage_pipeline,
            args=(code,),
            daemon=True
        )
        self.controls[code]["manager_thread"] = manager_thread
        manager_thread.start()

        logger.info(f"[{code}] Manager thread started with model for behavior: {behavior_code}")
        return True, "Detection starting"


    def stop_detection(self, code):
        """
        Stop detection for a given code.

        Args:
            code (str): The unique code for the control instance.

        Returns:
            tuple[bool, str]: (success, message)
        """
        if code not in self.controls:
            return False, f"No detection found for code: {code}"

        logger.info(f"[{code}] Signaling stop for detection.")
        # Signal all threads to stop
        self.controls[code]["stop_event"].set()

        # Wait for the manager thread to finish cleanup
        manager_thread = self.controls[code]["manager_thread"]
        if manager_thread.is_alive():
            logger.info(f"[{code}] Waiting for manager thread to join.")
            # Use configured timeout
            manager_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)

        # Check if the control entry was removed by the manager thread's cleanup
        if code in self.controls:
             # If still in controls after timeout, it might be stuck
             logger.warning(f"[{code}] Manager thread did not clean up within timeout.")
             # Attempt to clean up resources here if manager failed
             self._cleanup_control(code) # Force cleanup
             return False, "Failed to stop detection gracefully within timeout"
        else:
            logger.info(f"[{code}] Detection stopped and resources cleaned up.")
            return True, "Detection stopped successfully"

    def get_status(self, code):
        """
        Get status of detection for a given code.

        Args:
            code (str): The unique code for the control instance.

        Returns:
            dict: A dictionary containing the status information.
        """
        if code not in self.controls:
            # Return a structure similar to an inactive control for consistency
            return {
                "code": code,
                "behaviorCode": None,
                "streamUrl": None,
                "pushStream": False,
                "pushStreamUrl": None,
                "checkFps": 0.0,
                "status": "inactive",
                "uptime": 0.0,
                "error": "Control not found or inactive",
                "width": 0,
                "height": 0,
                "inputFps": 0.0
            }

        control = self.controls[code]
        # Calculate uptime based on start time
        uptime = time.time() - control.get("start_time", time.time())

        # Determine overall status based on internal state
        status = control.get("status", "unknown")
        if control["stop_event"].is_set():
            status = "stopping"
        elif control["error_event"].is_set():
             status = "error"
        elif not control["manager_thread"].is_alive():
             status = "stopped" # Manager thread exited unexpectedly?

        return {
            "code": code,
            "behaviorCode": control.get("behavior_code"),
            "streamUrl": control.get("stream_url"),
            "pushStream": control.get("push_stream"),
            "pushStreamUrl": control.get("push_stream_url"),
            "checkFps": control.get("fps", 0.0),
            "status": status,
            "uptime": uptime,
            "error": control.get("error", None),
            "width": control.get("width", 0),
            "height": control.get("height", 0),
            "inputFps": control.get("input_fps", 0.0)
        }

    def get_all_controls(self):
        """
        Get status of all active controls.

        Returns:
            list: A list of status dictionaries for all active controls.
        """
        controls_list = []
        # Iterate through keys to avoid issues if an item is removed during iteration
        for code in list(self.controls.keys()):
            # Get status for each control using the existing method
            controls_list.append(self.get_status(code))
        return controls_list

    def _manage_pipeline(self, code):
        """Manages the stream processing pipeline threads for a single control."""
        control = self.controls.get(code)
        if not control:
             logger.error(f"[{code}] Manager started but control entry not found.")
             return

        # ...existing code...
        stream_url = control["stream_url"]
        push_stream = control["push_stream"]
        push_stream_url = control["push_stream_url"]
        frame_queue = control["frame_queue"]
        annotated_frame_queue = control["annotated_frame_queue"]
        stop_event = control["stop_event"]
        error_event = control["error_event"]
        model = control["model"]  # 使用control专属的模型

        logger.info(f"[{code}] Pipeline manager started.")
        control["status"] = "running"

        # 传递模型给detector线程
        puller_thread = threading.Thread(
            target=self._pull_stream,
            args=(code, stream_url, frame_queue, stop_event, error_event, control),
            daemon=True
        )
        detector_thread = threading.Thread(
            target=self._detect_frames,
            args=(code, frame_queue, annotated_frame_queue, stop_event, error_event, model, control),
            daemon=True
        )
        pusher_thread = threading.Thread(
            target=self._push_stream,
            args=(code, annotated_frame_queue, push_stream, push_stream_url, stop_event, error_event, control),
            daemon=True
        )

        # ...existing code for thread management...
        control["puller_thread"] = puller_thread
        control["detector_thread"] = detector_thread
        control["pusher_thread"] = pusher_thread

        puller_thread.start()
        detector_thread.start()
        if push_stream:
            pusher_thread.start()

        logger.info(f"[{code}] Puller, Detector, Pusher threads started with behavior-specific model.")

        # ...existing code for monitoring and cleanup...
        try:
            while not stop_event.is_set() and not error_event.is_set():
                if not puller_thread.is_alive():
                    logger.error(f"[{code}] Puller thread died unexpectedly.")
                    error_event.set()
                    control["error"] = control.get("error", "Puller thread died unexpectedly.")
                    break
                if not detector_thread.is_alive():
                    logger.error(f"[{code}] Detector thread died unexpectedly.")
                    error_event.set()
                    control["error"] = control.get("error", "Detector thread died unexpectedly.")
                    break
                if push_stream and not pusher_thread.is_alive():
                    logger.error(f"[{code}] Pusher thread died unexpectedly.")
                    error_event.set()
                    control["error"] = control.get("error", "Pusher thread died unexpectedly.")
                    break

                time.sleep(MANAGER_CHECK_INTERVAL_SECONDS)

            logger.info(f"[{code}] Manager detected stop or error signal. Initiating shutdown.")

        except Exception as e:
            logger.exception(f"[{code}] Exception in manager thread: {e}")
            error_event.set()
            control["error"] = control.get("error", f"Exception in manager thread: {e}")

        finally:
            logger.info(f"[{code}] Manager initiating cleanup.")
            stop_event.set()

            timeout = THREAD_JOIN_TIMEOUT_SECONDS
            puller_thread.join(timeout=timeout)
            if puller_thread.is_alive():
                logger.warning(f"[{code}] Puller thread did not join within timeout.")
            detector_thread.join(timeout=timeout)
            if detector_thread.is_alive():
                logger.warning(f"[{code}] Detector thread did not join within timeout.")
            if push_stream:
                pusher_thread.join(timeout=timeout)
                if pusher_thread.is_alive():
                    logger.warning(f"[{code}] Pusher thread did not join within timeout.")

            self._cleanup_control(code)
            logger.info(f"[{code}] Manager finished cleanup and exited.")


    def _pull_stream(self, code, stream_url, frame_queue, stop_event, error_event, control):
        """Thread to pull frames from the video stream using OpenCV."""
        cap = None
        logger.info(f"[{code}] Puller thread started.")
        try:
            while not stop_event.is_set() and not error_event.is_set():
                if cap is None or not cap.isOpened():
                    logger.info(f"[{code}] Puller attempting to open stream: {stream_url}")
                    # Add configurations for specific stream types if needed (e.g., RTSP options)
                    # cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG) # Example using FFmpeg backend
                    cap = cv2.VideoCapture(stream_url)
                    if not cap.isOpened():
                        logger.warning(f"[{code}] Puller failed to open stream. Retrying in {STREAM_RECONNECT_DELAY_SECONDS} seconds.")
                        time.sleep(STREAM_RECONNECT_DELAY_SECONDS) # Wait before re-opening
                        continue # Try opening again
                    else:
                        logger.info(f"[{code}] Puller successfully opened stream.")
                        # Get stream properties once opened
                        control["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        control["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        control["input_fps"] = cap.get(cv2.CAP_PROP_FPS)
                        if control["input_fps"] <= 0:
                             logger.warning(f"[{code}] Puller could not get input stream FPS ({control['input_fps']}), defaulting to 25.0.")
                             control["input_fps"] = 25.0 # Default if FPS is zero or negative
                        logger.info(f"[{code}] Puller stream properties: {control['width']}x{control['height']} @ {control['input_fps']:.2f} fps")

                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning(f"[{code}] Puller received empty frame or stream ended (ret={ret}, frame is None={frame is None}). Attempting to re-open.")
                    if cap:
                        cap.release() # Release the old capture object
                    cap = None # Set cap to None to trigger re-opening in the next iteration
                    time.sleep(STREAM_RECONNECT_DELAY_SECONDS) # Wait a bit before trying to reconnect
                    continue # Continue loop to attempt re-opening

                # Put frame and timestamp into the queue (non-blocking if queue is full)
                try:
                    # Store raw frame and timestamp
                    frame_queue.put_nowait((frame, time.time()))
                except queue.Full:
                    # logger.warning(f"[{code}] Puller frame queue is full. Dropping frame.")
                    # Dropping frames is acceptable under load, no need to log excessively
                    pass # Drop the frame if the queue is full

        except Exception as e:
            logger.exception(f"[{code}] Exception in puller thread: {e}")
            error_event.set() # Signal error
            control["error"] = control.get("error", f"Exception in puller thread: {e}")

        finally:
            logger.info(f"[{code}] Puller thread cleaning up.")
            if cap:
                cap.release()
                logger.info(f"[{code}] Puller released video capture.")
            # Clear the queue on exit to prevent blocking consumers
            while not frame_queue.empty():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass # Queue is empty
            logger.info(f"[{code}] Puller thread exited.")


    def _detect_frames(self, code, frame_queue, annotated_frame_queue, stop_event, error_event, model, control):
        """
        Thread to perform object detection on frames and delegate to behavior logic.
        """
        logger.info(f"[{code}] Detector thread started.")
        frames_processed_interval = 0
        fps_update_time = time.time()

        # Wait for stream properties to be determined by the puller thread for buffer size
        # Use a loop with timeout
        timeout = THREAD_JOIN_TIMEOUT_SECONDS # Use configured timeout
        start_time = time.time()
        # Wait until input_fps is set and is positive
        while (control.get("input_fps", 0.0) <= 0.0) and not stop_event.is_set() and not error_event.is_set() and (time.time() - start_time) < timeout:
             logger.info(f"[{code}] Detector waiting for input_fps from puller...")
             time.sleep(0.1) # Short sleep while waiting

        input_fps = control.get("input_fps", 25.0) # Default if still not available or invalid
        # Set buffer maxlen based on input_fps and desired save duration
        buffer_maxlen = int(input_fps * VIDEO_SAVE_DURATION_SECONDS * 1.5) # Buffer a bit more than needed
        # Initialize or re-initialize frame_buffer with the correct maxlen
        control["frame_buffer"] = collections.deque(maxlen=max(1, buffer_maxlen)) # Ensure maxlen is at least 1
        logger.info(f"[{code}] Detector buffer maxlen set to {control['frame_buffer'].maxlen} frames (based on {input_fps:.2f} FPS).")

        # Instantiate the correct behavior handler based on behavior_code
        behavior_code = control["behavior_code"]
        behavior_handler = get_behavior_handler(behavior_code, code)

        if behavior_handler:
            behavior_handler.on_detection_start(control) # Call optional start method
            logger.info(f"[{code}] Loaded behavior handler: {behavior_handler.__class__.__name__}")
        else:
            logger.error(f"[{code}] Unknown or unsupported behavior code: {behavior_code}. No specific behavior logic will be applied.")
            # Set an error state if behavior handler couldn't be loaded
            error_event.set()
            control["error"] = control.get("error", f"Unsupported behavior code: {behavior_code}")
            return # Exit thread if behavior handler is critical and not found

        try:
            while not stop_event.is_set() and not error_event.is_set():
                try:
                    # Get frame and timestamp from the queue with a timeout
                    # Use configured timeout
                    frame, frame_timestamp = frame_queue.get(timeout=DETECTOR_QUEUE_GET_TIMEOUT)
                except queue.Empty:
                    # If queue is empty, check stop event and continue if not set
                    if stop_event.is_set() or error_event.is_set():
                        break # Exit loop if stopping or error
                    # No sleep needed here, timeout in get() handles waiting
                    continue # Try getting frame again

                # Run model on frame
                try:
                    # results is a list of Results objects
                    results = model(frame, verbose=False)
                    # results[0] contains the results for the first image (our frame)
                    # .plot() draws bounding boxes, masks, etc.
                    # .boxes.data.tolist() gives raw detection data [x1, y1, x2, y2, confidence, class_id]
                    annotated_frame = results[0].plot() if results and results[0] else frame.copy() # Use a copy if no results
                    detections = results[0].boxes.data.tolist() if results and results[0] else []
                except Exception as e:
                    logger.error(f"[{code}] Error during model inference or initial annotation: {str(e)}")
                    annotated_frame = frame.copy() # Use original frame copy if annotation fails
                    detections = [] # No valid detections


                # --- Delegate Behavior Logic ---
                event_triggered = False
                if behavior_handler:
                     # The behavior_handler processes the frame, potentially adds its own annotations,
                     # updates control_state, and signals if an event was triggered.
                    annotated_frame, event_triggered = behavior_handler.process_frame(annotated_frame, detections, control)

                if event_triggered:
                    # Handle the triggered event, e.g., start video saving
                    # Check if a save is already in progress to avoid multiple threads
                    if not control.get("is_saving_video", False) and not control.get("save_video_thread_active", False):
                        self.logger.info(f"[{code}] Behavior handler triggered an event. Initiating video save.")
                        # Set flags immediately
                        control["is_saving_video"] = True
                        control["save_video_thread_active"] = True

                        frames_to_save = list(control["frame_buffer"]) # Get frames from buffer
                        input_fps_for_save = control.get("input_fps", 25.0) # Use detected FPS or default
                        width_for_save = control.get("width", frame.shape[1] if frame is not None else 0)
                        height_for_save = control.get("height", frame.shape[0] if frame is not None else 0)
                        behavior_code_for_save = control.get("behavior_code")

                        # Get alarm data from the behavior handler
                        alarm_data = behavior_handler.get_alarm_data(control)
                        if not alarm_data:
                             self.logger.warning(f"[{code}] Behavior handler did not provide alarm data for triggered event.")
                             # Provide default alarm data if the behavior handler didn't
                             alarm_data = {"desc": f"行为代码: {behavior_code_for_save} (无详细描述)", "state": 0}

                        # Start a new thread to save the video using the utility function
                        # The utility function will create the Alarm record in SQLite.
                        # Pass the main controls dictionary so the utility function can update flags
                        save_video_thread = threading.Thread(
                            target=save_buffered_video, # Call the utility function
                            # Pass alarm_data and self.controls to the utility function
                            args=(code, frames_to_save, input_fps_for_save, width_for_save, height_for_save, behavior_code_for_save, alarm_data, self.controls),
                            daemon=True # Allow main program to exit
                        )
                        save_video_thread.start()

                    else:
                        # logger.debug(f"[{code}] Behavior event triggered, but video save is already in progress.")
                        pass # Do nothing if a save is already happening


                # --- End Delegate Behavior Logic ---

                # Add the final annotated frame to the buffer for potential saving
                # Ensure we append a copy if the frame object might be modified later
                control["frame_buffer"].append(annotated_frame.copy())


                # Put the final annotated frame into the output queue (non-blocking if queue is full)
                try:
                    annotated_frame_queue.put_nowait(annotated_frame)
                except queue.Full:
                    # logger.warning(f"[{code}] Detector annotated frame queue is full. Dropping frame.")
                    # Dropping annotated frames is acceptable under load
                    pass # Drop the frame if the queue is full

                # Mark the task as done for the item retrieved from the input queue
                frame_queue.task_done()

                # Update FPS stats
                frames_processed_interval += 1
                current_time = time.time()
                elapsed = current_time - fps_update_time
                # Update FPS using configured interval
                if elapsed > DETECTOR_FPS_UPDATE_INTERVAL:
                    control["fps"] = frames_processed_interval / elapsed
                    control["frames_processed"] = control.get("frames_processed", 0) + frames_processed_interval
                    frames_processed_interval = 0
                    fps_update_time = current_time

        except Exception as e:
            logger.exception(f"[{code}] Exception in detector thread: {e}")
            error_event.set() # Signal error
            control["error"] = control.get("error", f"Exception in detector thread: {e}")

        finally:
            logger.info(f"[{code}] Detector thread cleaning up.")
            if behavior_handler:
                 behavior_handler.on_detection_stop(control) # Call optional stop method

            # Mark any remaining items in the input queue as done if they were retrieved before stopping
            # This is tricky with get(timeout) and potential exceptions, but important for proper queue joining if used
            # For simplicity with daemon threads, we might skip explicit task_done for remaining items on exit.
            # Clear the output queue on exit
            while not annotated_frame_queue.empty():
                try:
                    annotated_frame_queue.get_nowait()
                except queue.Empty:
                    pass # Queue is empty
            logger.info(f"[{code}] Detector thread exited.")


    def _push_stream(self, code, annotated_frame_queue, push_stream, push_stream_url, stop_event, error_event, control):
        """Thread to push annotated frames via FFmpeg."""
        ffmpeg_process = None
        logger.info(f"[{code}] Pusher thread started.")

        if not push_stream or not push_stream_url:
            logger.info(f"[{code}] Pusher thread exiting: push_stream is not enabled or push_stream_url is missing.")
            return # Exit immediately if pushing is not enabled

        try:
            # Wait for stream properties to be determined by the puller thread
            # Use a loop with timeout
            timeout = THREAD_JOIN_TIMEOUT_SECONDS # Use configured timeout
            start_time = time.time()
            # Wait until width, height, and input_fps are set and valid
            while (control.get("width", 0) == 0 or control.get("height", 0) == 0 or control.get("input_fps", 0.0) <= 0.0) and not stop_event.is_set() and not error_event.is_set() and (time.time() - start_time) < timeout:
                 logger.info(f"[{code}] Pusher waiting for stream properties from puller...")
                 time.sleep(0.1) # Short sleep while waiting

            width = control.get("width", 0)
            height = control.get("height", 0)
            input_fps = control.get("input_fps", 0.0)

            if width == 0 or height == 0 or input_fps <= 0.0:
                 if not stop_event.is_set() and not error_event.is_set():
                     logger.error(f"[{code}] Pusher failed to get valid stream properties after timeout.")
                     error_event.set()
                     control["error"] = control.get("error", "Pusher failed to get stream properties from puller.")
                 logger.info(f"[{code}] Pusher thread exiting due to missing stream properties.")
                 return # Exit thread

            # Build FFmpeg command using utility function
            command = build_ffmpeg_push_command(push_stream_url, width, height, input_fps)

            if command is None:
                logger.error(f"[{code}] Pusher unsupported push stream URL protocol: {push_stream_url}")
                error_event.set()
                control["error"] = control.get("error", f"Pusher unsupported push stream URL protocol: {push_stream_url}")
                logger.info(f"[{code}] Pusher thread exiting due to unsupported protocol.")
                return # Exit thread

            logger.info(f"[{code}] Pusher starting FFmpeg process: {' '.join(command)}")

            try:
                # Use bufsize=0 for unbuffered pipe, which might help with low latency
                # Redirect stderr to PIPE to capture FFmpeg logs
                ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

                # Start a thread to read and log FFmpeg stderr
                def log_ffmpeg_output(process, code):
                    try:
                        for line in iter(process.stderr.readline, b''):
                            # Decode stderr bytes to string, ignoring errors
                            logger.info(f"[{code}] FFmpeg: {line.decode('utf-8', errors='ignore').strip()}")
                    except Exception as e:
                         logger.error(f"[{code}] Error reading FFmpeg stderr: {e}")
                    finally:
                        # Ensure stderr is closed
                        try:
                            process.stderr.close()
                        except Exception:
                            pass # Ignore errors on closing

                threading.Thread(target=log_ffmpeg_output, args=(ffmpeg_process, code), daemon=True).start()

            except FileNotFoundError:
                logger.error(f"[{code}] Pusher FFmpeg command not found. Is FFmpeg installed and in PATH?")
                error_event.set()
                control["error"] = control.get("error", "FFmpeg command not found.")
                logger.info(f"[{code}] Pusher thread exiting due to FFmpeg not found.")
                return # Exit thread
            except Exception as e:
                logger.error(f"[{code}] Pusher failed to start FFmpeg process: {str(e)}")
                error_event.set()
                control["error"] = control.get("error", f"Pusher failed to start FFmpeg: {str(e)}")
                logger.info(f"[{code}] Pusher thread exiting due to FFmpeg startup failure.")
                return # Exit thread

            logger.info(f"[{code}] FFmpeg process started successfully.")

            # Process annotated frames from the queue
            while not stop_event.is_set() and not error_event.is_set():
                # Check if FFmpeg process is still running
                if ffmpeg_process.poll() is not None:
                    logger.error(f"[{code}] Pusher FFmpeg process exited unexpectedly with code {ffmpeg_process.returncode}.")
                    error_event.set() # Signal error
                    control["error"] = control.get("error", f"Pusher FFmpeg process exited unexpectedly (code {ffmpeg_process.returncode}).")
                    break # Exit loop if FFmpeg died

                try:
                    # Get annotated frame from the queue with a timeout
                    # Use configured timeout
                    annotated_frame = annotated_frame_queue.get(timeout=PUSHER_QUEUE_GET_TIMEOUT)
                except queue.Empty:
                    # If queue is empty, check stop event and continue if not set
                    if stop_event.is_set() or error_event.is_set():
                        break # Exit loop if stopping or error
                    # No sleep needed here, timeout in get() handles waiting
                    continue # Try getting frame again

                # Push to FFmpeg stdin
                try:
                    # Ensure frame is contiguous before writing to pipe
                    if not annotated_frame.flags['C_CONTIGUOUS']:
                        annotated_frame = np.ascontiguousarray(annotated_frame)
                    # Write frame bytes to FFmpeg process's standard input
                    ffmpeg_process.stdin.write(annotated_frame.tobytes())
                    # No need to flush explicitly with bufsize=0, but doesn't hurt
                    # ffmpeg_process.stdin.flush()
                except BrokenPipeError:
                    logger.error(f"[{code}] Pusher FFmpeg pipe broken. FFmpeg process likely crashed or was stopped externally.")
                    error_event.set() # Signal error
                    control["error"] = control.get("error", "Pusher FFmpeg pipe broken.")
                    break # Exit loop if pipe is broken
                except Exception as e:
                    logger.error(f"[{code}] Pusher error writing to FFmpeg stdin: {str(e)}")
                    error_event.set() # Signal error
                    control["error"] = control.get("error", f"Pusher error writing to FFmpeg stdin: {str(e)}")
                    break # Exit loop on other FFmpeg write errors

                # Mark the task as done for the item retrieved from the queue
                annotated_frame_queue.task_done()

        except Exception as e:
            logger.exception(f"[{code}] Exception in pusher thread: {e}")
            error_event.set() # Signal error
            control["error"] = control.get("error", f"Exception in pusher thread: {e}")

        finally:
            logger.info(f"[{code}] Pusher thread cleaning up.")
            if ffmpeg_process:
                try:
                    # Attempt to close stdin gracefully first
                    if ffmpeg_process.stdin and not ffmpeg_process.stdin.closed:
                         try:
                             # Send 'q' to FFmpeg stdin to quit gracefully (might not work for rawvideo input)
                             # Or just close stdin to signal end of input
                             ffmpeg_process.stdin.close()
                             logger.info(f"[{code}] Pusher closed FFmpeg stdin.")
                         except Exception as e:
                             logger.warning(f"[{code}] Error closing FFmpeg stdin: {e}")

                    # Wait for FFmpeg to exit, with a timeout
                    # Use configured timeout
                    return_code = ffmpeg_process.wait(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
                    logger.info(f"[{code}] Pusher FFmpeg process exited with code {return_code}.")
                except subprocess.TimeoutExpired:
                    logger.warning(f"[{code}] Pusher FFmpeg process did not exit within timeout, killing it.")
                    try:
                        ffmpeg_process.kill()
                        # Wait a bit more after killing
                        ffmpeg_process.wait(timeout=2)
                    except Exception as e:
                        logger.error(f"[{code}] Error killing FFmpeg process: {e}")
                except Exception as e:
                    logger.error(f"[{code}] Pusher error during FFmpeg cleanup: {str(e)}")

            # Mark any remaining items in the input queue as done
            # This is tricky with get(timeout) and potential exceptions, but important for proper queue joining if used
            # For simplicity with daemon threads, we might skip explicit task_done for remaining items on exit.
            logger.info(f"[{code}] Pusher thread exited.")


    def _cleanup_control(self, code):
        """
        Cleans up resources associated with a control code.
        Called by the manager thread or stop_detection if manager fails.
        """
        logger.info(f"[{code}] Performing final control cleanup.")
        # Get the control dictionary safely, as it might have been partially removed
        control = self.controls.get(code)
        if not control:
            logger.warning(f"[{code}] Control entry not found during cleanup.")
            return # Nothing to clean up if already gone

        # Ensure stop event is set
        control["stop_event"].set()

        # Attempt to join threads if they are still around (should have been joined by manager, but belt and suspenders)
        threads_to_join = ["puller_thread", "detector_thread", "pusher_thread", "manager_thread"]
        for thread_name in threads_to_join:
            thread = control.get(thread_name)
            if thread and thread.is_alive():
                logger.warning(f"[{code}] Cleanup: {thread_name} is still alive, attempting join.")
                try:
                    # Use a short timeout for final join
                    thread.join(timeout=2)
                    if thread.is_alive():
                         logger.error(f"[{code}] Cleanup: {thread_name} failed to join.")
                    else:
                         logger.info(f"[{code}] Cleanup: {thread_name} joined successfully.")
                except Exception as e:
                     logger.error(f"[{code}] Cleanup: Error joining {thread_name}: {e}")

        # Clear queues to release references to frames
        queues_to_clear = ["frame_queue", "annotated_frame_queue"]
        for queue_name in queues_to_clear:
            q = control.get(queue_name)
            if q:
                logger.info(f"[{code}] Cleanup: Clearing {queue_name}.")
                while not q.empty():
                    try:
                        # Use get_nowait() with a try-except to safely clear
                        q.get_nowait()
                        # If task_done was consistently called on get, uncomment this:
                        # try: q.task_done() except ValueError: pass
                    except queue.Empty:
                        pass # Queue is empty, stop clearing
                    except Exception as e:
                        logger.error(f"[{code}] Cleanup: Error getting item from {queue_name} during clear: {e}")
                # After clearing, check if the queue is empty
                if q.empty():
                    logger.info(f"[{code}] Cleanup: {queue_name} is empty.")
                else:
                    logger.warning(f"[{code}] Cleanup: {queue_name} might not be fully empty.")


        # Remove the control entry from the main controls dictionary
        if code in self.controls:
            logger.info(f"[{code}] Removing control entry from self.controls.")
            try:
                del self.controls[code]
                logger.info(f"[{code}] Control entry removed.")
            except KeyError:
                logger.warning(f"[{code}] Control entry already removed during cleanup.")
            except Exception as e:
                logger.error(f"[{code}] Error removing control entry: {e}")

        logger.info(f"[{code}] Control cleanup complete.")

