# 视频告警系统
这个系统是我的本科毕业设计，主要是包含了web系统、目标检测算法、大模型聊天界面设计等方面，如果有同学也想改进一下用来做毕业设计，那么目前的web系统不需要再去从零开始重新写了，只需要把自己构思的目标检测算法层面或者业务层面的改进创新（我这里用的是Ultralytics）在**media**目录中的部署起来，再在**Admin**中去注册算法。同时，如果有需要做大模型相关的改进，可以自己构建一个Restful 服务器，在**Admin下的ai_chat_google**中对应修改。
## 系统架构

- **后端**：基于 **Django 5** 框架（Python 3.11），集成开放词汇目标检测（如 YOLO-World/YOLO-E）与多模态大语言模型（Google Ai Studio），实现视频监控场景下的智能告警与辅助分析。
- **前端**：采用 colorlib的WordPress模板，支持多路视频流实时监控、目标检测结果可视化与任务管理。
- **视频输入与转发**：支持本地摄像头、网络流等多协议视频输入，利用 ZLMediaKit 实现流转发与多终端播放（HLS/FLV/RTMP/RTSP）。

## 核心功能

- ✅ **用户与权限管理**：基于 Django Admin，支持多用户协作与权限分级，保障系统安全。
- ✅ **视频流管理**：支持多路视频流的接入、管理与实时监控。
- ✅**目标检测与缺陷识别**：集成微调后的 YOLO-World/YOLO-E 模型，实现对绝缘子等关键设备的开放词汇检测与缺陷识别。
- ✅ **布控与告警任务**：支持行为分析任务的配置、实时告警与历史记录管理，适应复杂场景。
- ✅ **多模态智能问答**：基于 Google Ai studio，结合检测结果与告警文本，实现多模态智能问答与辅助决策。

## 典型流程

1. 管理员登录后台，添加/管理视频流。
2. 配置目标检测与缺陷识别任务，实时查看检测与告警结果。
3. 管理布控任务、导出历史分析与告警记录。
4. 利用多模态大模型进行故障原因分析、处理建议与报告生成。

## 部署与扩展

- 支持本地或服务器部署，灵活适配视频检测实际需求。
- 可扩展接入更多 AI 模型、数据源与多模态分析能力，持续提升系统智能化水平。


#Admin 视频实时告警系统 后台管理

#### 环境
| 程序         | 版本               |
| ---------- |------------------|
| python     | 3.11             |
| 依赖库      | requirements.txt |

### 安装依赖库
~~~
conda create your_env_name pyrhon=3.11
pip install -r requriments.txt
conda activate your_env_name
~~~

### 启动顺序

~~~
1.启动后台管理服务
    进入 admin 路径下
    python manage.py runserver 0.0.0.0:9001

2.接入视频流
    进入 zlm 路径下，启动ZLMediaKit流媒体服务器

3.模拟推送视频流
    进入 data 路径下 使用ffmpeg模拟推送视频流

4.启动视频检测的Restful服务器
    进入 media 路径
    python app.py
~~~
## 界面展示
- 控制面板
![控制面板](./images/control%20pannel.png)
- 视频流管理
![视频流管理](./images/video%20stream%20manage.png)
- 视频流预览
![视频流预览](./images/video%20steam%20preview.png)
- 布控管理
![布控管理](./images/deployment%20manage.png)
- 算法管理
![算法管理](./images/algorithm%20manage.png)
- 告警页面
![告警页面](./images/alarm%20page.png)
- Web AI
![Web AI](./images/ai%20chat.png)
## 结语
喜欢的可以点个star，有什么问题可以提提issue
