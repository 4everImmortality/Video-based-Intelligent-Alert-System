# inference_service/behaviors/InsulatorBehavior.py (Standalone with SQLite)

import cv2
import numpy as np
from .base_behavior import BaseBehavior

class InsulatorBehavior(BaseBehavior):
    """
    Behavior to detect insulators using a specialized trained model.
    专门检测绝缘子的行为处理器，使用单独训练的绝缘子检测权重
    """
    def __init__(self, control_code):
        """
        Initializes the Insulator behavior handler.
        Args:
            control_code (str): The unique code for the control instance.
        """
        super().__init__(control_code)
        # 专门训练的模型不需要类别配置，所有检测结果都是绝缘子
        self.logger.info("Insulator behavior initialized with specialized insulator detection model")

    def process_frame(self, frame: np.ndarray, detections: list, control_state: dict) -> tuple[np.ndarray, bool]:
        """
        Processes the frame to detect insulators and draw bounding boxes.
        处理帧以检测绝缘子并绘制边界框
        
        Args:
            frame (np.ndarray): The current frame (already has general detections drawn).
            detections (list): Raw detection results from specialized insulator model.
            control_state (dict): The mutable state dictionary for this control code.

        Returns:
            tuple[np.ndarray, bool]:
                - np.ndarray: The frame with insulator detections drawn.
                - bool: Always False, as this behavior only does detection visualization.
        """
        # 在帧的副本上绘制检测结果，避免修改缓冲区帧
        annotated_frame = frame.copy()
        
        insulator_count = len(detections)  # 所有检测结果都是绝缘子
        

        # 在画面左上角显示绝缘子总数
        count_text = f"Insulators Detected: {insulator_count}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        color = (0, 255, 0)  # 绿色
        thickness = 2
        position = (10, 35)  # 左上角位置
        
        # 绘制计数文本的背景
        text_size = cv2.getTextSize(count_text, font, font_scale, thickness)[0]
        cv2.rectangle(annotated_frame, 
                    (position[0] - 5, position[1] - text_size[1] - 10),
                    (position[0] + text_size[0] + 5, position[1] + 5),
                    (0, 0, 0), -1)  # 黑色背景
        
        # 绘制计数文本
        cv2.putText(annotated_frame, count_text, position, font, font_scale, color, thickness)

        # 在右上角显示模型信息
        model_info_text = "Specialized Insulator Model"
        model_info_position = (annotated_frame.shape[1] - 300, 30)  # 右上角
        cv2.putText(annotated_frame, model_info_text, model_info_position, 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)  # 青色文字

        # 如果检测到绝缘子，在左下角显示状态信息
        if insulator_count > 0:
            status_text = f"Status: {insulator_count} insulator(s) monitored"
            status_position = (10, annotated_frame.shape[0] - 20)  # 左下角
            cv2.putText(annotated_frame, status_text, status_position, 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)  # 黄色文字

        # 这个behavior只做检测显示，不触发特定事件如视频保存
        event_triggered = False

        return annotated_frame, event_triggered

    # This behavior does not trigger alarms, so get_alarm_data is not needed
    # or can return None as per the BaseBehavior default.