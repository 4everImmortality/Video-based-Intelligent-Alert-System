from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
import json
# Import the generativeai library
from google import genai # Using genai as the alias as in your original code
from google.genai import types # Import types for Content and Part
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q # Import Q for complex lookups
import base64 # Import base64 for decoding
import traceback # Import traceback for detailed error printing

# Assuming your models are in an app named 'app'
# from .models import ChatHistory, ChatMessage
# Replace with the actual import path to your models
from app.models import ChatHistory, ChatMessage # Make sure this path is correct

@csrf_exempt
def ai_chat_google_api(request):
    """
    API endpoint for Google Gemini chat using the google-generativeai SDK.
    Handles sending messages (text and images) and receiving responses (streaming or non-streaming).
    Saves chat history to the database for unauthenticated users (using a fixed user_id).
    """
    # Authentication is removed as per previous request.
    # For unauthenticated users, we use a fixed user_id for conversation history.
    user_id = 0 # Fixed user ID for unauthenticated access. Consider using sessions for per-user history.

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        # Get conversation_id from the request data. Null for a new chat.
        conversation_id = data.get('conversation_id')
        # Messages array from frontend, includes history for the current turn.
        messages = data.get('messages', [])
        api_key = data.get('api_key')
        stream = data.get('stream', False) # Boolean to indicate streaming response

        if not api_key:
            return JsonResponse({'success': False, 'error': '未提供API密钥'}, status=400)

        if not messages:
            return JsonResponse({'success': False, 'error': '消息不能为空'}, status=400)

        # Find or create ChatHistory for the fixed user_id
        if conversation_id:
            try:
                # Attempt to find the existing conversation for the fixed user_id
                chat_history = get_object_or_404(ChatHistory, id=conversation_id, user_id=user_id)
            except:
                 # If conversation_id is provided but not found or doesn't match user_id,
                 # treat this as a request to start a new conversation.
                 chat_history = ChatHistory.objects.create(user_id=user_id, title="新对话")
                 conversation_id = chat_history.id # Update conversation_id with the new one
        else:
            # If no conversation_id is provided, create a new conversation.
            chat_history = ChatHistory.objects.create(user_id=user_id, title="新对话")
            conversation_id = chat_history.id # Get the ID of the newly created conversation


        # --- Create a client instance using genai.Client() ---
        # According to the README, generate_content is called on client.models
        client = genai.Client(api_key=api_key)


        # Convert messages to the format expected by the GenAI SDK (List of Content objects)
        # For multi-turn conversations, the `contents` list should contain alternating
        # 'user' and 'model' roles, representing the history.
        # We reconstruct the history from the database for accuracy.

        # Fetch existing messages for this conversation from the database, ordered by creation time.
        db_messages = chat_history.messages.order_by('created_at')

        contents = []
        for db_msg in db_messages:
            # Map Django model roles to GenAI API roles
            # 'user' in model -> 'user' in API
            # 'assistant' in model -> 'model' in API
            api_role = 'user' if db_msg.role == 'user' else 'model'
            parts = []
            if db_msg.content:
                 # Add text part
                 parts.append(types.Part.from_text(text=db_msg.content))
            if db_msg.image_data:
                 # Add image part if image_data exists
                 # Assuming image_data is base64 string without the data URL prefix (e.g., "data:image/jpeg;base64,")
                 image_data_base64 = db_msg.image_data
                 mime_type = 'image/jpeg' # Default MIME type

                 # Attempt to extract MIME type from data URL prefix if it exists
                 if ',' in image_data_base64:
                     prefix, image_data_base64 = image_data_base64.split(',', 1)
                     if prefix.startswith('data:'):
                         mime_part = prefix.split(':', 1)[1]
                         if ';' in mime_part:
                             mime_type = mime_part.split(';', 1)[0]
                         else:
                             mime_type = mime_part

                 # --- Debugging Print Statement ---
                 print(f"Processing image data for history. Base64 length: {len(image_data_base64) if image_data_base64 else 0}, Starts with: {image_data_base64[:50] if image_data_base64 else 'N/A'}")
                 print(f"Determined MIME type: {mime_type}")
                 # --- End Debugging Print Statement ---

                 try:
                     # Decode base64 string to bytes
                     image_bytes = base64.b64decode(image_data_base64)
                     # Use types.Part.from_bytes()
                     parts.append(
                          types.Part.from_bytes(
                              data=image_bytes,
                              mime_type=mime_type
                          )
                     )
                 except Exception as e:
                     print(f"Error decoding base64 image data for history: {e}")
                     traceback.print_exc()
                     # Optionally, add an error message to the chat or skip this part


            # Add the message content to the contents list if it has any parts
            if parts:
                 contents.append(
                     types.Content(
                         role=api_role,
                         parts=parts
                     )
                 )

        # Add the *current* user message being sent from the frontend to the contents list.
        # This is the latest message the user just typed/sent.
        current_user_message_data = messages[-1] if messages else None # Get the last message from frontend list
        if current_user_message_data and current_user_message_data.get('role') == 'user':
             current_user_parts = []
             if current_user_message_data.get('content'):
                 current_user_parts.append(types.Part.from_text(text=current_user_message_data['content']))
             if current_user_message_data.get('image'):
                 image_data_base64 = current_user_message_data['image']
                 mime_type = 'image/jpeg' # Default MIME type

                 # Attempt to extract MIME type from data URL prefix if it exists
                 if ',' in image_data_base64:
                     prefix, image_data_base64 = image_data_base64.split(',', 1)
                     if prefix.startswith('data:'):
                         mime_part = prefix.split(':', 1)[1]
                         if ';' in mime_part:
                             mime_type = mime_part.split(';', 1)[0]
                         else:
                             mime_type = mime_part


                 # --- Debugging Print Statement ---
                 print(f"Processing current image data. Base64 length: {len(image_data_base64) if image_data_base64 else 0}, Starts with: {image_data_base64[:50] if image_data_base64 else 'N/A'}")
                 print(f"Determined MIME type: {mime_type}")
                 # --- End Debugging Print Statement ---

                 try:
                     # Decode base64 string to bytes
                     image_bytes = base64.b64decode(image_data_base64)
                      # Use types.Part.from_bytes()
                     current_user_parts.append(
                          types.Part.from_bytes(
                              data=image_bytes,
                              mime_type=mime_type
                          )
                     )
                 except Exception as e:
                     print(f"Error decoding base64 current image data: {e}")
                     traceback.print_exc()
                     # Return an error response if the current image cannot be processed
                     return JsonResponse({'success': False, 'error': f'处理图片失败: {e}'}, status=400)


             # Add the current user message to the contents list if it has parts
             if current_user_parts:
                 contents.append(
                     types.Content(
                         role='user',
                         parts=current_user_parts
                     )
                 )

             # Save the current user message to the database
             # Save base64 data without the prefix to the database
             ChatMessage.objects.create(
                 chat=chat_history,
                 role='user',
                 content=current_user_message_data.get('content', ''),
                 image_data=image_data_base64 if current_user_message_data.get('image') else None
             )

        # --- Call the Generative Model API ---
        # The core interaction with the Google GenAI API happens here.

        if stream:
            # Handle streaming response
            def generate_stream():
                bot_response_content = ""
                try:
                    # Use the generate_content_stream method on client.models
                    stream_response = client.models.generate_content_stream(
                            model='gemini-2.0-flash', # Specify the model name
                            contents=contents, # Pass the conversation history and current user message
                    )
                    # Iterate over the response chunks
                    for chunk in stream_response:
                        chunk_text = chunk.text or ''
                        bot_response_content += chunk_text
                        # Yield each chunk as a JSON string
                        yield json.dumps({'chunk': chunk_text}) + '\n'

                    # After the stream is complete, save the full bot response to the database
                    ChatMessage.objects.create(
                        chat=chat_history,
                        role='assistant',
                        content=bot_response_content
                    )
                    # Update chat history title if it's the first bot message in a new chat
                    # Check if there are exactly 2 messages (the initial user message + this first assistant message)
                    if chat_history.messages.count() == 2 and chat_history.title == "新对话":
                        # Use the first few words of the bot response as title
                        first_words = bot_response_content.split()[:5]
                        chat_history.title = " ".join(first_words) + "..." if len(first_words) > 0 else "新对话"
                        chat_history.save()


                except genai.errors.APIError as e:
                    # Handle API specific errors
                    yield json.dumps({'success': False, 'error': f"API error: {e.message}"}) + '\n'
                except Exception as e:
                    # Handle any other unexpected errors
                    yield json.dumps({'success': False, 'error': str(e)}) + '\n'

            # Return the conversation_id as a first chunk in the stream
            # This helps the frontend identify the conversation ID for a newly created chat.
            def stream_with_id():
                 yield json.dumps({'conversation_id': conversation_id}) + '\n'
                 yield from generate_stream() # Yield chunks from the main streaming function

            return StreamingHttpResponse(stream_with_id(), content_type='application/json')

        else:
            # Handle non-streaming response
            # Use the generate_content method on client.models
            response = client.models.generate_content(
                model='gemini-2.0-flash', # Specify the model name
                contents=contents, # Pass the conversation history and current user message
            )
            response_text = response.text # Get the full response text

            # Save the bot response to the database
            ChatMessage.objects.create(
                chat=chat_history,
                role='assistant',
                content=response_text
            )
             # Update chat history title if it's the first bot message in a new chat
            # Check if there are exactly 2 messages (the initial user message + this first assistant message)
            if chat_history.messages.count() == 2 and chat_history.title == "新对话":
                # Use the first few words of the bot response as title
                first_words = response_text.split()[:5]
                chat_history.title = " ".join(first_words) + "..." if len(first_words) > 0 else "新对话"
                chat_history.save()


            return JsonResponse({
                'success': True,
                'conversation_id': conversation_id, # Return the conversation ID
                'response': response_text, # Return the full response text
            })

    except json.JSONDecodeError:
        # Handle invalid JSON in the request body
        return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
    except genai.errors.APIError as e:
        # Handle API specific errors (e.g., invalid API key, rate limits)
        print(f"Google Gemini API error: {e.code} - {e.message}")
        return JsonResponse({'success': False, 'error': f"API error: {e.message}"}, status=500)
    except Exception as e:
        # Handle any other unexpected errors during processing
        # Print the full traceback for better debugging
        traceback.print_exc()
        print(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def get_conversations(request):
    """
    API endpoint to get a list of chat conversations for the current user.
    Uses a fixed user_id for unauthenticated access.
    """
    # Authentication is removed as per previous request.
    user_id = 0 # Fixed user ID for unauthenticated access

    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET method is allowed'}, status=405)

    # Get all chat histories for the fixed user_id, ordered by updated_at descending
    conversations = ChatHistory.objects.filter(user_id=user_id).order_by('-updated_at')

    conversation_list = []
    for conv in conversations:
        # Determine the display title for the conversation
        display_title = conv.title
        # If the title is the default "新对话", try to use the first user message content
        if display_title == "新对话":
             first_user_message = conv.messages.filter(role='user').order_by('created_at').first()
             if first_user_message and first_user_message.content:
                 # Use the first 30 characters of the first user message as title
                 display_title = first_user_message.content[:30] + "..." if len(first_user_message.content) > 30 else first_user_message.content
             else:
                 display_title = "新对话" # Fallback if no user message yet

        conversation_list.append({
            'id': conv.id,
            'title': display_title,
            'timestamp': int(conv.updated_at.timestamp() * 1000) # Timestamp in milliseconds for frontend sorting
        })

    return JsonResponse({'success': True, 'conversations': conversation_list})


@csrf_exempt
def get_conversation_messages(request, conversation_id):
    """
    API endpoint to get messages for a specific conversation.
    Uses a fixed user_id for unauthenticated access and ensures the conversation belongs to this user_id.
    """
    # Authentication is removed as per previous request.
    user_id = 0 # Fixed user ID for unauthenticated access

    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET method is allowed'}, status=405)

    try:
        # Fetch the chat history ensuring it belongs to the fixed user_id
        chat_history = get_object_or_404(ChatHistory, id=conversation_id, user_id=user_id)
        # Fetch all messages for this conversation, ordered by creation time
        messages = chat_history.messages.order_by('created_at')

        message_list = []
        for msg in messages:
            message_list.append({
                'role': msg.role, # 'user' or 'assistant'
                'content': msg.content, # Text content of the message
                'image': msg.image_data, # Base64 image data if any
                'timestamp': int(msg.created_at.timestamp() * 1000) # Timestamp in milliseconds
            })

        return JsonResponse({'success': True, 'messages': message_list, 'conversation_id': conversation_id})

    except:
        # Return 404 if the conversation is not found or doesn't belong to the user_id
        return JsonResponse({'success': False, 'error': '对话未找到或无权访问'}, status=404)


@csrf_exempt
def delete_conversation(request, conversation_id):
    """
    API endpoint to delete a specific conversation.
    Uses a fixed user_id for unauthenticated access and ensures the conversation belongs to this user_id.
    """
    # Authentication is removed as per previous request.
    user_id = 0 # Fixed user ID for unauthenticated access

    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Only DELETE method is allowed'}, status=405)

    try:
        # Fetch the chat history ensuring it belongs to the fixed user_id and delete it
        chat_history = get_object_or_404(ChatHistory, id=conversation_id, user_id=user_id)
        chat_history.delete() # Deletes the ChatHistory and related ChatMessages due to CASCADE
        return JsonResponse({'success': True, 'message': '对话已删除'})
    except:
        # Return 404 if the conversation is not found or doesn't belong to the user_id
        return JsonResponse({'success': False, 'error': '对话未找到或无权访问'}, status=404)

# Remember to add these views to your urls.py
# Example urls.py entries:
# from . import views # Or from your_app_name import views
# path('api/ai_chat_google/', views.ai_chat_google_api, name='ai_chat_google_api'),
# path('api/conversations/', views.get_conversations, name='get_conversations'),
# path('api/conversations/<int:conversation_id>/', views.get_conversation_messages, name='get_conversation_messages'),
# path('api/conversations/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
