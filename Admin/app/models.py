import os

from django.db import models
from django.utils import timezone
import logging

# Import settings here to ensure it's available in methods
from django.conf import settings

logger = logging.getLogger(__name__)


# Based on CREATE TABLE "av_notification"
class Notification(models.Model):
    # The SQL has an auto-incrementing primary key 'id', which Django creates by default
    sort = models.IntegerField(verbose_name='排序')
    title = models.CharField(max_length=100, verbose_name='标题') # SQL has varchar(100)
    content = models.CharField(max_length=200, verbose_name='内容') # SQL has varchar(200)

    # SQL has datetime NOT NULL, auto_now_add=True and auto_now=True are appropriate for create/update times
    create_time = models.DateTimeField(auto_now_add=True,verbose_name='创建时间')
    last_update_time = models.DateTimeField(auto_now=True,verbose_name='更新时间') # Changed to auto_now=True

    state = models.IntegerField(default=0, verbose_name='状态') # SQL has INTEGER NOT NULL DEFAULT 0

    def __repr__(self):
        return self.title

    def __str__(self):
        return self.title

    class Meta:
        # managed = True # Remove managed=True unless you are managing the table creation outside Django
        db_table = 'av_notification' # Matches SQL table name
        verbose_name = '通知'
        verbose_name_plural = '通知'


# Based on CREATE TABLE "av_control"
class Control(models.Model):
    # The SQL has an auto-incrementing primary key 'id', which Django creates by default
    user_id = models.IntegerField(default=0, verbose_name='用户') # SQL has i NOT NULL DEFAULT 0 (assuming 'i' means integer)
    sort = models.IntegerField(verbose_name='排序') # SQL has integer NOT NULL
    code = models.CharField(max_length=50, verbose_name='编号') # SQL has varchar(50) NOT NULL

    stream_app = models.CharField(max_length=50, verbose_name='视频流应用') # SQL has varchar(50) NOT NULL
    stream_name = models.CharField(max_length=100, verbose_name='视频流名称') # SQL has varchar(100) NOT NULL
    stream_video = models.CharField(max_length=100, verbose_name='视频流视频') # SQL has varchar(100) NOT NULL
    stream_audio = models.CharField(max_length=100, verbose_name='视频流音频') # SQL has varchar(100) NOT NULL

    behavior_code = models.CharField(max_length=50, verbose_name='算法行为编号') # SQL has varchar(50) NOT NULL
    # Note: SQL has interval, sensitivity, overlap_thresh in av_behavior, but also in av_control.
    # This might indicate these are specific settings per control, overriding behavior defaults.
    # Keeping them in Control as per SQL.
    interval = models.IntegerField(default=0, verbose_name='检测间隔') # SQL has INTEGER NOT NULL DEFAULT 0
    sensitivity = models.FloatField(default=0.0, verbose_name='灵敏度') # SQL has INTEGER NOT NULL DEFAULT 0 (Changed to FloatField based on typical sensitivity values and av_behavior definition)
    overlap_thresh = models.FloatField(default=0.0, verbose_name='阈值') # SQL has integer NOT NULL DEFAULT 0 (Changed to FloatField based on typical threshold values and av_behavior definition)
    remark = models.CharField(max_length=200, verbose_name='备注') # SQL has varchar(200) NOT NULL

    push_stream = models.BooleanField(verbose_name='是否推流') # SQL has INTEGER NOT NULL (BooleanField is appropriate)
    push_stream_app = models.CharField(max_length=50, null=True, blank=True, verbose_name='推流应用') # SQL has varchar(50) (Added blank=True for admin form)
    push_stream_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='推流名称') # SQL has varchar(100) (Added blank=True for admin form)

    state = models.IntegerField(default=0,verbose_name="布控状态") # SQL has INTEGER NOT NULL DEFAULT 0 # 0：未布控  1：布控中  5：布控中断

    # SQL has datetime NOT NULL, auto_now_add=True and auto_now=True are appropriate
    create_time = models.DateTimeField(auto_now_add=True,verbose_name='创建时间')
    last_update_time = models.DateTimeField(auto_now=True,verbose_name='更新时间') # Changed to auto_now=True

    def __repr__(self):
        return self.code

    def __str__(self):
        return self.code

    class Meta:
        db_table = 'av_control' # Matches SQL table name
        verbose_name = '布控'
        verbose_name_plural = '布控'

# Based on CREATE TABLE "av_camera"
class Camera(models.Model):
    # The SQL has an auto-incrementing primary key 'id', which Django creates by default
    sort = models.IntegerField(verbose_name='排序') # SQL has integer NOT NULL
    code = models.CharField(max_length=50, verbose_name='摄像头编号') # SQL has varchar(50) NOT NULL
    name = models.CharField(max_length=100, verbose_name='摄像头名称') # SQL has varchar(100) NOT NULL
    stream_name = models.CharField(max_length=200,verbose_name='视频流名称') # SQL has varchar(200) NOT NULL
    stream_state = models.BooleanField(verbose_name='视频流状态') # SQL has BooleanField (assuming INTEGER in SQL is used for boolean)
    state = models.BooleanField(verbose_name='状态') # SQL has BooleanField (assuming INTEGER in SQL is used for boolean)
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='备注') # SQL has varchar(200) null=True (Added blank=True)
    # SQL has datetime NOT NULL, auto_now_add=True and auto_now=True are appropriate
    create_time = models.DateTimeField(auto_now_add=True,verbose_name='创建时间')
    last_update_time = models.DateTimeField(auto_now=True,verbose_name='更新时间') # Changed to auto_now=True

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'av_camera' # Matches SQL table name
        verbose_name = '摄像头'
        verbose_name_plural = '摄像头'


# Based on CREATE TABLE "av_behavior"
class Behavior(models.Model):
    # The SQL has an auto-incrementing primary key 'id', which Django creates by default
    # SQL has a unique constraint on 'code'
    code = models.CharField(max_length=50, unique=True, verbose_name='算法编号') # SQL has varchar(50) NOT NULL UNIQUE
    name = models.CharField(max_length=100, verbose_name='算法名称') # SQL has varchar(50) NOT NULL (Increased max_length to 100 as in your original model, or change to 50 if strictly following SQL)
    # Note: SQL has sort, name_en, state which are not in your original Behavior model.
    # Adding them based on SQL.
    sort = models.IntegerField(default=0, verbose_name='排序') # SQL has integer NOT NULL (Added default=0)
    name_en = models.CharField(max_length=50, default='', verbose_name='算法英文名称') # SQL has varchar(50) NOT NULL (Added default='')
    state = models.IntegerField(default=0, verbose_name='状态') # SQL has INTEGER NOT NULL DEFAULT 0

    interval = models.IntegerField(default=10, verbose_name='检测间隔') # SQL has integer NOT NULL, your default 10 is fine
    sensitivity = models.FloatField(default=0.5, verbose_name='灵敏度') # SQL has float NOT NULL DEFAULT NULL (Changed default to 0.5, FloatField is correct)
    overlap_thresh = models.FloatField(default=0.45, verbose_name='阈值') # SQL has float NOT NULL (FloatField is correct)
    remark = models.TextField(null=True, blank=True, verbose_name='备注') # SQL has TEXT NOT NULL (Changed to TextField, added null=True, blank=True as in your original model, or remove if strictly following SQL NOT NULL)

    class Meta:
        db_table = 'av_behavior' # Matches SQL table name
        verbose_name = '算法'
        verbose_name_plural = '算法'
        # SQL includes a 'sort' column, you might want to add default ordering here
        ordering = ['sort'] # Example ordering by sort

    def __str__(self):
        return self.name


# Based on av_chat_history (assuming from your original models.py)
class ChatHistory(models.Model):
    # The SQL has an auto-incrementing primary key 'id', which Django creates by default
    title = models.CharField(max_length=255, blank=True)
    user_id = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Changed to auto_now=True
    model_name = models.CharField(max_length=50, default="gemma-3-4b")

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        db_table = 'av_chat_history' # Assuming this is the table name


# Based on av_chat_message (assuming from your original models.py)
class ChatMessage(models.Model):
    # The SQL has an auto-incrementing primary key 'id', which Django creates by default
    chat = models.ForeignKey(ChatHistory, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20)  # user or assistant
    content = models.TextField()
    image_data = models.TextField(blank=True, null=True)  # Base64 image data if any
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        db_table = 'av_chat_message' # Assuming this is the table name


# Based on av_alarm (assuming from your original models.py and our previous discussion)
# Assuming no specific SQL for av_alarm was provided, keeping the existing model structure.
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

