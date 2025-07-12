# inference_service/behaviors/zhoujieruqin.py (Standalone with SQLite)

import time
import cv2
import numpy as np
from behaviors.base_behavior import BaseBehavior
from config import VIDEO_SAVE_DURATION_SECONDS

class ZhouJieRuQinBehavior(BaseBehavior):
    """
    Behavior to detect continuous presence of a person for a defined duration
    and trigger a video save and Alarm creation.
    """
    def __init__(self, control_code):
        """
        Initializes the ZHOUJIERUQIN behavior handler.

        Args:
            control_code (str): The unique code for the control instance.
        """
        super().__init__(control_code)
        self.logger.info("ZHOUJIERUQIN behavior handler initialized.")

    def on_detection_start(self, control_state: dict):
        """
        Initializes behavior-specific state in the control dictionary.
        """
        super().on_detection_start(control_state)
        # Initialize state variables in the control_state dictionary
        control_state["person_detected_since"] = None  # Timestamp when person was first detected continuously
        # is_saving_video and save_video_thread_active flags are managed by VideoProcessor,
        # but the behavior sets the condition that triggers the save.

    def process_frame(self, frame: np.ndarray, detections: list, control_state: dict) -> tuple[np.ndarray, bool]:
        """
        Checks for continuous person detection and triggers video save event.

        Args:
            frame (np.ndarray): The current frame (already has general detections drawn).
            detections (list): Raw detection results.
            control_state (dict): The mutable state dictionary for this control code.

        Returns:
            tuple[np.ndarray, bool]:
                - np.ndarray: The frame (no additional annotations for this behavior).
                - bool: True if the video save condition is met, False otherwise.
        """
        current_time = time.time()
        person_detected_in_frame = False
        # Assuming class 0 in detections is 'person' in the YOLO model
        person_detections = [det for det in detections if int(det[5]) == 0]

        if person_detections:
            person_detected_in_frame = True

        # Get state from control_state
        person_detected_since = control_state.get("person_detected_since")
        is_saving_video = control_state.get("is_saving_video", False) # Check the flag managed by VideoProcessor

        event_triggered = False

        if person_detected_in_frame:
            if person_detected_since is None:
                # First time person detected in a continuous sequence
                control_state["person_detected_since"] = current_time
                self.logger.info(f"Person first detected at {current_time:.2f}.")
            else:
                # Person detected continuously, check duration
                duration = current_time - person_detected_since
                # logger.debug(f"Person detected continuously for {duration:.2f} seconds.")
                if duration >= VIDEO_SAVE_DURATION_SECONDS and not is_saving_video:
                    self.logger.warning(f"Person detected for >= {VIDEO_SAVE_DURATION_SECONDS} seconds. Triggering video save.")
                    # Signal the event_triggered flag to the VideoProcessor.
                    # The VideoProcessor will then set its internal saving flags
                    # and start the save thread.
                    event_triggered = True
        else:
            # Person not detected in this frame
            if person_detected_since is not None:
                # Person was detected, but not anymore - reset timer
                self.logger.info("Person no longer detected. Resetting timer.")
                control_state["person_detected_since"] = None
                # The is_saving_video flag is reset by the save_buffered_video utility function
                # or by the VideoProcessor's event handling if the save was triggered.
                # If a save was in progress and person disappears, the save will still complete
                # for the buffered frames.

        # No additional annotations are added by this behavior to the frame itself.
        return frame, event_triggered

    def get_alarm_data(self, control_state: dict) -> dict | None:
        """
        Provides data for the Alarm record when a save is triggered by this behavior.
        """
        # This method is called by VideoProcessor when event_triggered is True.
        # We return the relevant data for the Alarm record insertion.
        return {
            "desc": f"行为代码: ZHOUJIERUQIN - 检测到人员持续入侵超过 {VIDEO_SAVE_DURATION_SECONDS} 秒",
            "state": 0 # means not read yet
        }

