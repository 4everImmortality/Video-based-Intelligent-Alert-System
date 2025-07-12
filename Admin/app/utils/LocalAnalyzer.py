import time
import requests
import threading
import json
import logging
from datetime import datetime
from framework.settings import ConfigObj


class Analyzer:
    def __init__(self):
        """Initialize analyzer as a client to Flask inference service"""
        self.active_controls = {}  # Store active controls in memory
        self.flask_api_url = ConfigObj["analyzerApiHost"]
        self.logger = logging.getLogger(__name__)

    def controls(self):
        """Get all active controls"""
        try:
            response = requests.get(f"{self.flask_api_url}/controls")
            if response.status_code == 200:
                controls_list = response.json().get("controls", [])
                return True, "success", controls_list
            return False, f"Failed to get controls: {response.status_code}", []
        except Exception as e:
            self.logger.error(f"Failed to get controls: {str(e)}")
            return False, str(e), []

    def control(self, code):
        """Get details for a specific control"""
        try:
            response = requests.get(f"{self.flask_api_url}/control/{code}")
            if response.status_code == 200:
                return True, "success", response.json()
            return False, "Control not found", {}
        except Exception as e:
            return False, str(e), {}

    def control_add(self, code, behaviorCode, streamUrl, pushStream, pushStreamUrl):
        """Add a new control by sending request to Flask app"""
        try:
            # Create control in local tracking
            control = {
                "code": code,
                "behaviorCode": behaviorCode,
                "streamUrl": streamUrl,
                "pushStream": pushStream,
                "pushStreamUrl": pushStreamUrl if pushStream else None,
                "checkFps": 0.0,
                "status": "active",
                "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Store locally to track state
            self.active_controls[code] = control

            # Send to Flask app
            data = {
                "code": code,
                "behavior_code": behaviorCode,
                "stream_url": streamUrl,
                "push_stream": pushStream,
                "push_stream_url": pushStreamUrl
            }

            response = requests.post(f"{self.flask_api_url}/start_detection", json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    # Start a thread to update FPS stats
                    threading.Thread(target=self._update_stats, args=(code,), daemon=True).start()
                    return True, "布控添加成功"
                return False, result.get("message", "Unknown error")
            return False, f"Failed to add control: {response.status_code}"
        except Exception as e:
            self.logger.error(f"Failed to add control: {str(e)}")
            if code in self.active_controls:
                del self.active_controls[code]
            return False, str(e)

    def control_cancel(self, code):
        """Cancel a control by sending request to Flask app"""
        try:
            if code in self.active_controls:
                response = requests.post(f"{self.flask_api_url}/stop_detection", json={"code": code})

                # Mark as stopping regardless of response to ensure cleanup
                self.active_controls[code]["status"] = "stopping"

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        # Remove from active controls
                        if code in self.active_controls:
                            del self.active_controls[code]
                        return True, "布控取消成功"
                    return False, result.get("message", "Unknown error")
                return False, f"Failed to cancel control: {response.status_code}"
            return False, "布控不存在"
        except Exception as e:
            self.logger.error(f"Failed to cancel control: {str(e)}")
            if code in self.active_controls:
                del self.active_controls[code]
            return False, str(e)

    def _update_stats(self, code):
        """Update stats for an active control by polling Flask app"""
        while code in self.active_controls and self.active_controls[code]["status"] == "active":
            try:
                response = requests.get(f"{self.flask_api_url}/status/{code}")
                if response.status_code == 200:
                    result = response.json()
                    if code in self.active_controls:
                        self.active_controls[code]["checkFps"] = result.get("fps", 0.0)
                time.sleep(2)  # Poll every 2 seconds
            except Exception as e:
                self.logger.error(f"Error updating stats for {code}: {str(e)}")
                time.sleep(5)  # Back off on error