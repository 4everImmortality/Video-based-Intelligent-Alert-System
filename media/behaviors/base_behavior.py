# inference_service/behaviors/base_behavior.py (Standalone with SQLite)

import abc
import logging
import numpy as np

logger = logging.getLogger(__name__)

class BaseBehavior(abc.ABC):
    """
    Base class for defining custom detection behaviors.
    All specific behaviors should inherit from this class.
    """
    def __init__(self, control_code):
        """
        Initializes the base behavior handler.

        Args:
            control_code (str): The unique code for the control instance.
        """
        self.control_code = control_code
        # Create a logger specific to this behavior instance for easier debugging
        self.logger = logging.getLogger(f"[{self.control_code}] {self.__class__.__name__}")
        self.logger.info("Behavior handler initialized.")

    @abc.abstractmethod
    def process_frame(self, frame: np.ndarray, detections: list, control_state: dict) -> tuple[np.ndarray, bool]:
        """
        Process a single frame based on the behavior logic.
        This method should implement the core detection logic for the behavior.

        Args:
            frame (np.ndarray): The current frame (potentially already annotated with general detections).
            detections (list): A list of raw detection results from the model
                               (e.g., [x1, y1, x2, y2, confidence, class_id] for each detection).
            control_state (dict): The mutable state dictionary for this control code.
                                   Behaviors can read and update their state here.

        Returns:
            tuple[np.ndarray, bool]:
                - np.ndarray: The frame after applying behavior-specific annotations.
                - bool: True if an event requiring action (like saving video or triggering alarm)
                        was triggered by this frame, False otherwise.
        """
        pass

    def on_detection_start(self, control_state: dict):
        """
        Optional method called when the detection starts for this behavior.
        Use this for any setup needed at the beginning of processing a stream.

        Args:
            control_state (dict): The mutable state dictionary for this control code.
        """
        self.logger.info("Behavior started.")
        # Example: Initialize behavior-specific state variables in control_state
        # control_state['behavior_specific_counter'] = 0

    def on_detection_stop(self, control_state: dict):
        """
        Optional method called when the detection stops for this behavior.
        Use this for any cleanup needed at the end of processing a stream.

        Args:
            control_state (dict): The mutable state dictionary for this control code.
        """
        self.logger.info("Behavior stopped.")
        # Example: Log final state or perform cleanup
        # final_count = control_state.get('behavior_specific_counter', 0)
        # self.logger.info(f"Final count: {final_count}")


    def get_alarm_data(self, control_state: dict) -> dict | None:
        """
        Optional method to provide data for creating an Alarm record
        when a behavior event is triggered.

        Args:
            control_state (dict): The mutable state dictionary for this control code.

        Returns:
            dict | None: A dictionary containing data for the Alarm (e.g., {"desc": "...", "state": ...}),
                         or None if no specific alarm data is available from the behavior.
                         This data will be passed to the save_buffered_video function.
        """
        return None # Default: no specific alarm data from the behavior

