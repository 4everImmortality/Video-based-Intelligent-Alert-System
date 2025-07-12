import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# --- Media Files Settings ---
# URL that handles the media served from MEDIA_ROOT. Use a trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Directory within MEDIA_ROOT where alarm videos will be saved.
# This should match the VIDEO_SAVE_DIR in your detection service code,
# but relative to MEDIA_ROOT.
# Example: If VIDEO_SAVE_DIR in your detection service is "saved_videos",
# and MEDIA_ROOT is "/path/to/your/project/media/",
# then the full path where videos are saved is "/path/to/your/project/media/saved_videos/"
# Your detection service should save files using paths relative to MEDIA_ROOT,
# e.g., "saved_videos/alarm_code_timestamp.mp4"
VIDEO_SAVE_DIR_RELATIVE = 'saved_videos' # Relative path within MEDIA_ROOT

# You can derive the absolute path for the detection service if needed:
# VIDEO_SAVE_DIR_ABSOLUTE = os.path.join(MEDIA_ROOT, VIDEO_SAVE_DIR_RELATIVE)
# --- End Media Files Settings ---
