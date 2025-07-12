import logging

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from app.views.ViewsBase import *
from app.models import *
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from app.utils.Utils import validate_email, validate_tel, gen_random_code, gen_control_code
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)

# Assuming VIDEO_SAVE_DIR is configured in settings.py
# VIDEO_SAVE_DIR = os.path.join(settings.BASE_DIR, 'saved_videos')
# And MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'media')
# And you have configured Django to serve MEDIA_ROOT under MEDIA_URL

def web_test_alarms(request):
    return render(request, 'app/web_test_alarm.html')

def web_alarms(request):
    """
    View to display the alarm management page with pagination.
    Handles GET requests to /alarms.
    """
    top_msg = "报警列表" # Default message

    # Get pagination parameters from request
    page_number = request.GET.get('p', 1) # Default to page 1
    page_size = request.GET.get('ps', 10) # Default to 10 items per page

    try:
        page_size = int(page_size)
        if page_size <= 0:
             page_size = 10 # Ensure valid page size
    except ValueError:
        page_size = 10 # Default if ps is not a valid integer

    # Fetch all alarms, ordered by creation time (newest first, as defined in model Meta)
    alarm_list = Alarm.objects.all()

    # --- Add Logging Here ---
    logger.info(f"Fetched {alarm_list.count()} alarms from the database.")
    # --- End Logging ---


    # Set up pagination
    paginator = Paginator(alarm_list, page_size)

    try:
        alarms_page = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        alarms_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        alarms_page = paginator.page(paginator.num_pages)

    # Prepare data for the template
    data_for_template = []
    for alarm in alarms_page:
        data_for_template.append({
            "id": alarm.alarm_id,
            "imageUrl": alarm.get_image_url(), # Use the model method to get URL
            "videoUrl": alarm.get_video_url(), # Use the model method to get URL
            "state": alarm.state,
            "desc": alarm.desc,
            "create_time": alarm.create_time.strftime("%Y-%m-%d %H:%M:%S") # Format time
        })

    # --- Add Logging Here ---
    logger.info(f"Prepared {len(data_for_template)} items for the template.")
    # logger.debug(f"Data for template: {data_for_template}") # Log the actual data (be cautious with sensitive info)
    # --- End Logging ---


    # Prepare pagination data for the template
    page_labels = []
    # Simple pagination labels (e.g., 1, 2, 3, ..., Last)
    # You might want more sophisticated pagination logic here
    if alarms_page.has_previous():
         page_labels.append({"name": "上一页", "page": alarms_page.previous_page_number(), "cur": 0})

    # Add current page and a few around it
    start_page = max(1, alarms_page.number - 2)
    end_page = min(paginator.num_pages, alarms_page.number + 2)

    if start_page > 1:
        page_labels.append({"name": 1, "page": 1, "cur": 0})
        if start_page > 2:
             page_labels.append({"name": "...", "page": "#", "cur": 0}) # Ellipsis

    for i in range(start_page, end_page + 1):
         page_labels.append({"name": i, "page": i, "cur": 1 if i == alarms_page.number else 0})

    if end_page < paginator.num_pages:
        if end_page < paginator.num_pages - 1:
             page_labels.append({"name": "...", "page": "#", "cur": 0}) # Ellipsis
        page_labels.append({"name": paginator.num_pages, "page": paginator.num_pages, "cur": 0})

    if alarms_page.has_next():
        page_labels.append({"name": "下一页", "page": alarms_page.next_page_number(), "cur": 0})


    page_data = {
        "page_num": paginator.num_pages, # Total number of pages
        "count": paginator.count,       # Total number of items
        "page_size": page_size,
        "pageLabels": page_labels,
        # You can add more pagination details if needed, e.g., current page number
    }


    context = {
        'top_msg': top_msg,
        'data': data_for_template,
        'pageData': page_data,
    }

    return render(request, 'app/web_alarms.html', context) # Assuming your template is in app/templates/app/


def serve_alarm_video(request, alarm_id):
    """
    一个代理视图，用于从服务器的绝对路径流式传输视频文件。
    """
    # 1. 根据URL传入的alarm_id，从数据库获取对应的Alarm对象
    #    如果找不到，get_object_or_404会自动返回404错误页面
    alarm = get_object_or_404(Alarm, pk=alarm_id)

    # 2. 从模型实例中获取视频文件的绝对路径
    video_path = alarm.video_absolute_path

    # 3. 检查路径是否存在，如果不存在或路径为空，则返回404
    if not video_path or not os.path.exists(video_path):
        raise Http404("请求的视频文件不存在或路径已失效。")

    # 4. 使用FileResponse来发送文件。
    #    FileResponse是专门为发送文件而优化的，它会自动处理MIME类型、
    #    Content-Length等HTTP头，并且以流式方式发送，避免一次性将大文件读入内存。
    try:
        # 'rb' 表示以二进制只读方式打开文件
        return FileResponse(open(video_path, 'rb'))
    except FileNotFoundError:
        raise Http404("视频文件未找到。")


def web_test(request):
    context = {
        "title": "测试",
        "msg": "测试"
    }
    return render(request, 'app/test.html', context)

def web_index(request):
    context = {

    }

    return render(request, 'app/web_index.html', context)

def web_stream(request):
    context = {
    }

    # data = Camera.objects.all().order_by("-sort")

    return render(request, 'app/web_stream.html',context)

def web_stream_play(request):
    context = {
    }
    params = parse_get_params(request)
    app = params.get("app",None)
    name = params.get("name",None)

    if app and name:
        context["url"] = base_media.get_flvUrl(app, name)
    else:
        return render(request, 'app/message.html', {"msg": "请通过视频流管理进入", "is_success": False, "redirect_url": "/stream"})

    context["url_true"] = True
    return render(request, 'app/web_stream_play.html', context)


def web_control(request):
    context = {
    }

    return render(request, 'app/web_control.html', context)


def web_control_add(request):
    # Generate a unique code for new control
    control_code = f"control_{int(time.time())}"

    # Create an empty control object with default values (not saved to DB yet)
    control = Control(
        code=control_code,
        user_id=getUser(request).get("id") if getUser(request) else 0,
        sort=0,
        interval=1,
        sensitivity=1,
        overlap_thresh=1,
        stream_app="",
        stream_name="",
        stream_video="",
        stream_audio="",
        behavior_code="",
        push_stream=False,
        push_stream_app=base_media.default_push_stream_app,
        push_stream_name=control_code,
        remark=""
    )

    # Get available streams
    try:
        streams = base_media.getMediaList()
    except Exception:
        streams = []

    # Query all behaviors (algorithms) using ORM
    behaviors = Behavior.objects.all().order_by('name')

    # Prepare context for template
    context = {
        'handle': 'add',
        'control': control,
        'streams': streams,
        'behaviors': behaviors,
        'control_stream_flvUrl': ''
    }

    return render(request, 'app/web_control_handle.html', context)

def web_control_edit(request):
    """
    Edit an existing control using Django ORM
    """
    user = getUser(request)
    if not user:
        return redirect('/login')

    code = request.GET.get('code')
    if not code:
        return redirect('/control')

    try:
        # Get the control object using Django ORM
        control = Control.objects.get(code=code)

        # Get all behaviors using Django ORM
        behaviors = Behavior.objects.all()

        # Get the flv URL for the stream
        control_stream_flvUrl = base_media.get_flvUrl(control.stream_app, control.stream_name)

        # Prepare context data for template
        context = {
            'user': user,
            'control': control,
            'behaviors': behaviors,
            'control_stream_flvUrl': control_stream_flvUrl,
            'handle': 'edit'
        }

        return render(request, 'app/web_control_handle.html', context)
    except Control.DoesNotExist:
        return redirect('/control')
    except Exception as e:
        print(f"Error in web_control_edit: {e}")
        return redirect('/control')

def web_warning(request):
    context = {

    }
    return render(request, 'warning.html', context)


def web_notification(request):
    context = {

    }
    return render(request, 'notification.html', context)


# app/views/web.py (update the web_behavior function)
from app.models import Behavior


def web_behavior(request):
    context = {}
    # Use ORM to get behaviors directly
    context["data"] = Behavior.objects.all().values()
    return render(request, 'app/web_behavior.html', context)


def web_profile(request):
    context = {

    }
    return render(request, 'profile.html', context)


def web_logout(request):
    if request.session.has_key(base_session_key_user):
        del request.session[base_session_key_user]

    return redirect("/")


def web_login(request):
    context = {

    }

    if request.method == 'POST':
        code = 0
        msg = "error"

        params = parse_post_params(request)

        username = params.get("username")
        password = params.get("password")
        verify_code = params.get("verify_code")

        context["username"] = username
        context["password"] = password
        context["verify_code"] = verify_code

        session_verify_code = request.session.get("login_verify_code")
        if True or session_verify_code:
            if True or verify_code == session_verify_code:
                try:
                    del request.session["login_verify_code"]
                except:
                    pass

                if validate_email(username):
                    try:
                        user = User.objects.get(email=username)
                    except:
                        user = None
                    if not user:
                        msg = "邮箱未注册"
                else:
                    user = User.objects.get(username=username)
                    if not user:
                        msg = "用户名未注册"
                if user:
                    if user.check_password(password):
                        if user.is_active:
                            user.last_login = datetime.now()
                            user.save()
                            request.session["user"] = {
                                "id": user.id,
                                "username": username,
                                "email": user.email,
                                "last_login": user.last_login.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            code = 1000
                            msg = "登录成功"
                        else:
                            msg = "账号已禁用"
                    else:
                        msg = "密码错误"
            else:
                msg = "验证码错误"
        else:
            code = -10
            msg = "验证码已过期"

        res = {
            "code": code,
            "msg": msg
        }
        return HttpResponseJson(res)

    return render(request, 'app/web_login.html', context)


# Add to app/views/web.py
def web_test_camera(request):
    """Test camera access"""
    return render(request, 'app/web_test_camera.html', {})


def web_ai_chat_google(request):
    """AI Chat interface using Google AI Studio API"""
    return render(request, 'app/web_ai_chat_google.html', {})