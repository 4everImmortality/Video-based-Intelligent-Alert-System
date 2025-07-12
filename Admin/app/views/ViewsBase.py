# 修改导入语句
import json
import os
# 将原有导入替换为新实现
from app.utils.ZLMediaKit import ZLMediaKit
from app.utils.Analyzer import Analyzer
# from app.utils.LocalAnalyzer import Analyzer
from app.utils.DjangoSql import DjangoSql
from django.http import HttpResponse
import time
from datetime import datetime

from framework.settings import ConfigObj

base_media = ZLMediaKit(ConfigObj=ConfigObj)
# 为本地 Analyzer 提供模型路径
base_analyzer = Analyzer(ConfigObj.get("analyzerApiHost"))

base_session_key_user = "user"

# 以下保持不变
def getUser(request):
    user = request.session.get(base_session_key_user)
    return user

def parse_get_params(request):
    params = {}
    for k in request.GET:
        params.__setitem__(k, request.GET.get(k))
    return params

def parse_post_params(request):
    params = {}
    for k in request.POST:
        params.__setitem__(k, request.POST.get(k))
    return params

def HttpResponseJson(res):
    def json_dumps_default(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            raise TypeError
    return HttpResponse(json.dumps(res, default=json_dumps_default), content_type="application/json")