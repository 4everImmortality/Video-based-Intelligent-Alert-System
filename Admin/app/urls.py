from django.urls import path, re_path

from framework import settings
from .views.ai_chat import *
from .views.web import *
from .views.api import *
from django.conf.urls.static import static

app_name = 'app'

urlpatterns = [
    path('', web_index),
    path('stream', web_stream),
    path('stream/play', web_stream_play),

    path('test_alarm', web_test_alarms),
    path('alarms/', web_alarms, name='alarms_list'),
    path('api/postHandleAlarm', handle_alarm_api, name='handle_alarm_api'),

    path('stream/test', web_test),

    path('behavior', web_behavior),

    # Add these URL patterns
    path('api/addAlgorithm', api_addAlgorithm),
    path('api/editAlgorithm', api_editAlgorithm),
    path('api/deleteAlgorithm', api_deleteAlgorithm),

    path('control', web_control),
    path('control/add', web_control_add),
    path('control/edit', web_control_edit),
    path('api/deleteControl', api_delete_control, name='api_delete_control'),
    path('warning', web_warning),
    path('profile', web_profile),
    path('notification', web_notification),
    path('login', web_login),
    path('logout', web_logout),

    path('controlAdd', api_controlAdd),
    path('controlEdit', api_controlEdit),
    path('analyzerControlAdd', api_analyzerControlAdd),
    path('analyzerControlCancel', api_analyzerControlCancel),
    path('getControls', api_getControls),
    path('getIndex', api_getIndex),
    path('getStreams', api_getStreams),
    path('getVerifyCode', api_getVerifyCode),
    path('test-camera', web_test_camera),

    # Google Gemini Chat API
    path('ai_chat_google/', web_ai_chat_google, name='ai_chat'),
    path('api/ai_chat_google/', ai_chat_google_api, name='ai_chat_google_api'),

    # Conversation management APIs
    path('api/conversations/', get_conversations, name='get_conversations'),
    path('api/conversations/<int:conversation_id>/', get_conversation_messages, name='get_conversation_messages'),
    path('api/conversations/<int:conversation_id>/delete/', delete_conversation, name='delete_conversation'),

]
