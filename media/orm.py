import os

from django.db import models
from django.utils import timezone
import logging

# Import settings here to ensure it's available in methods
from django.conf import settings

class Alarm(models.Model):
    """
    Model to store alarm video information.
    """
    # Unique identifier for the alarm, could be linked to the control code
    # or a unique ID generated when the alarm video is saved.
    # Using CharField for flexibility, assuming it comes from the detection service.
    # SQL primary key is often 'id', but using alarm_id as primary key is also valid if it's guaranteed unique.
    # If your SQL table uses 'id' as PK and 'alarm_id' as a regular unique field, you'll need to adjust this.
    alarm_id = models.CharField(max_length=255, unique=True, primary_key=True)

    # Path to the saved video file relative to MEDIA_ROOT (for frontend URL)
    video_path = models.CharField(max_length=500)

    # --- New field to store the absolute path ---
    # This field will store the full file system path for backend operations (like deletion)
    video_absolute_path = models.CharField(max_length=500, blank=True, null=True, verbose_name='视频绝对路径')
    # --- End New field ---

    # Path to the poster image file relative to MEDIA_ROOT (optional)
    image_path = models.CharField(max_length=500, blank=True, null=True)

    # Description of the alarm (e.g., "周界入侵")
    desc = models.CharField(max_length=255)

    # Status of the alarm: 0 for unread, 1 for read
    state = models.IntegerField(default=0) # 0: 未读, 1: 已读

    # Timestamp when the alarm occurred/was recorded
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Order alarms by creation time, newest first
        ordering = ['-create_time']
        db_table = 'av_alarm' # Assuming the table name is av_alarm
        verbose_name = '告警' # Added verbose_name
        verbose_name_plural = '告警' # Added verbose_name_plural


    def __str__(self):
        return f"Alarm {self.alarm_id} - {self.desc}"

    def get_video_url(self):
        """Returns the absolute URL for the video file (for frontend)."""
        # Assumes video_path is relative to MEDIA_ROOT
        # Need to import settings if not already done at the top
        # from django.conf import settings # Already imported at the top
        if self.video_path:
            return os.path.join(settings.MEDIA_URL, self.video_path).replace('\\', '/') # Use forward slashes for URL
        return None # Or a default video URL/placeholder

    def get_image_url(self):
        """Returns the absolute URL for the image poster file (for frontend)."""
        # Assumes image_path is relative to MEDIA_ROOT
        # from django.conf import settings # Already imported at the top
        if self.image_path:
            return os.path.join(settings.MEDIA_URL, self.image_path).replace('\\', '/') # Use forward slashes for URL
        return None # Or a default image URL/placeholder

    def delete(self, *args, **kwargs):
        """
        Override delete to also remove the associated video and image files using the absolute path.
        """
        # Need to import settings if not already done at the top
        # from django.conf import settings # Already imported at the top
        # import os # Already imported at the top
        # import logging # Already imported at the top

        # logger = logging.getLogger(__name__) # Get logger instance - already done at top

        # --- Use the absolute path for deletion ---
        video_full_path = self.video_absolute_path

        # --- Add Detailed Logging Here ---
        logger.info(f"[{self.alarm_id}] Attempting to delete video file.")
        logger.info(f"[{self.alarm_id}] Using absolute path for deletion: {video_full_path}")
        # --- End Detailed Logging ---

        # Remove video file
        if video_full_path and os.path.exists(video_full_path): # Check if path is not empty and exists
            try:
                os.remove(video_full_path)
                logger.info(f"[{self.alarm_id}] Successfully deleted video file: {video_full_path}")
            except OSError as e:
                logger.error(f"[{self.alarm_id}] Error deleting video file {video_full_path}: {e}", exc_info=True) # Log exception info
            except Exception as e: # Catch any other potential exceptions during removal
                 logger.error(f"[{self.alarm_id}] Unexpected error during video file deletion {video_full_path}: {e}", exc_info=True)
        elif video_full_path: # Log if path was provided but file not found
             logger.warning(f"[{self.alarm_id}] Attempted to delete video file at path but it was not found: {video_full_path}")
        else: # Log if video_absolute_path was empty
             logger.warning(f"[{self.alarm_id}] video_absolute_path is empty for alarm {self.alarm_id}. Cannot delete file.")


        # Remove image file if it exists (similar logic, add logging here too)
        # Assuming image_path is relative, construct full path using MEDIA_ROOT
        if self.image_path:
            image_full_path = os.path.join(settings.MEDIA_ROOT, self.image_path)
            logger.info(f"[{self.alarm_id}] Attempting to delete image file at relative path: {self.image_path}")
            logger.info(f"[{self.alarm_id}] Constructed image full path: {image_full_path}")
            if os.path.exists(image_full_path):
                 try:
                    os.remove(image_full_path)
                    logger.info(f"[{self.alarm_id}] Successfully deleted image file: {image_full_path}")
                 except OSError as e:
                    logger.error(f"[{self.alarm_id}] Error deleting image file {image_full_path}: {e}", exc_info=True)
                 except Exception as e:
                    logger.error(f"[{self.alarm_id}] Unexpected error during image file deletion {image_full_path}: {e}", exc_info=True)
            else:
                 logger.warning(f"[{self.alarm_id}] Attempted to delete image file but it was not found: {image_full_path}")


        # Call the parent delete method
        super().delete(*args, **kwargs)
        logger.info(f"[{self.alarm_id}] Deleted Alarm object from database.")