# inference_service/behaviors/renshutongji.py (Standalone with SQLite)

import cv2
import numpy as np
from .base_behavior import BaseBehavior
from config import BEHAVIOR_CLASSES_MAP

class RenShuTongJiBehavior(BaseBehavior):
    """
    Behavior to count the number of people detected in a frame and display the count.
    支持开放词汇模型，可以检测特定类别
    """
    def __init__(self, control_code):
        """
        Initializes the RENSHUTONGJI behavior handler.

        Args:
            control_code (str): The unique code for the control instance.
        """
        super().__init__(control_code)
        # 获取该behavior配置的检测类别
        self.target_classes = BEHAVIOR_CLASSES_MAP.get("RENSHUTONGJI", ["person"])
        self.logger.info(f"RENSHUTONGJI behavior initialized with target classes: {self.target_classes}")

    def process_frame(self, frame: np.ndarray, detections: list, control_state: dict) -> tuple[np.ndarray, bool]:
        """
        Counts people and draws the count on the frame.
        支持多种检测类别的计数

        Args:
            frame (np.ndarray): The current frame (already has general detections drawn).
            detections (list): Raw detection results.
            control_state (dict): The mutable state dictionary for this control code.

        Returns:
            tuple[np.ndarray, bool]:
                - np.ndarray: The frame with the people count drawn.
                - bool: Always False, as this behavior doesn't trigger specific events like video save.
        """
        # 对于开放词汇模型，检测结果可能包含类别名称而不是数字ID
        # 需要根据实际模型输出格式调整检测逻辑
        
        person_count = 0
        
        # 遍历所有检测结果
        for det in detections:
            try:
                # 检查检测结果的格式
                if len(det) >= 6:
                    # 标准格式: [x1, y1, x2, y2, confidence, class_id/class_name]
                    class_info = det[5]
                    
                    # 判断类别信息是字符串还是数字
                    if isinstance(class_info, str):
                        # 开放词汇模型返回类别名称
                        if class_info.lower() in [cls.lower() for cls in self.target_classes]:
                            person_count += 1
                    else:
                        # 传统模型返回类别ID，假设0是person类
                        if int(class_info) == 0:  # 假设person的class_id是0
                            person_count += 1
                            
            except (IndexError, ValueError, TypeError) as e:
                self.logger.debug(f"Error processing detection: {det}, error: {e}")
                continue

        # Draw the count on a copy of the frame to avoid modifying the buffer frame directly
        annotated_frame = frame.copy()
        
        # Define text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        color = (0, 255, 0)  # Green color (BGR format)
        thickness = 2
        
        # 构建显示文本，显示检测的类别和数量
        if len(self.target_classes) == 1 and self.target_classes[0].lower() == "person":
            text = f"People Count: {person_count}"
        else:
            classes_str = "/".join(self.target_classes)
            text = f"{classes_str} Count: {person_count}"
            
        position = (10, 30)  # Top-left corner

        # Draw the text on the frame
        cv2.putText(annotated_frame, text, position, font, font_scale, color, thickness)
        
        # 可选：在右上角显示检测的类别信息
        class_info_text = f"Classes: {', '.join(self.target_classes)}"
        class_info_position = (annotated_frame.shape[1] - 300, 30)  # Top-right corner
        cv2.putText(annotated_frame, class_info_text, class_info_position, 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

        # This behavior does not trigger specific events
        event_triggered = False

        return annotated_frame, event_triggered

    # This behavior does not trigger alarms, so get_alarm_data is not needed
    # or can return None as per the BaseBehavior default.