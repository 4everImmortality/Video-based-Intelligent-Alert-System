## 🚨 Video-based Intelligent Alert System

This project is my undergraduate thesis, focusing on a web-based intelligent monitoring and alert platform that integrates target detection models and multimodal large language models.
 If you're also considering a similar system for your final project, this framework allows you to plug in your own detection algorithms or business-specific logic without rebuilding the entire stack from scratch.

------

### 🧱 System Architecture

- **Backend**: Built on Django 5 (Python 3.11), integrates open-vocabulary object detection (YOLO-World/YOLO-E) and multimodal large language models (via Google AI Studio) for intelligent analysis in video surveillance scenarios.
- **Frontend**: Customized from Colorlib's WordPress template, supporting multi-channel live video preview, detection result visualization, and task management.
- **Video Input & Streaming**: Supports webcam, RTSP, and other protocols; powered by ZLMediaKit for live streaming (HLS/RTMP/FLV/RTSP) to multiple endpoints.

------

### ⚙️ Core Features

✅ **User & Permission Management**
 Role-based access control via Django Admin for secure multi-user collaboration.

✅ **Multi-stream Video Monitoring**
 Real-time preview and centralized control of multiple video sources.

✅ **Object Detection & Fault Identification**
 Custom fine-tuned YOLO-World or YOLO-E models deployed for open-vocabulary detection of key components like insulators and identifying potential faults.

✅ **Alert Task Configuration**
 Define behavioral or visual patterns to monitor. Real-time alerts and full logging for review and decision-making.

✅ **Multimodal Question Answering**
 Based on Google AI Studio, combining detection results and alerts for intelligent Q&A and fault analysis.

------

### 🔁 Typical Workflow

1. Admin logs in and registers video streams.
2. Configure detection tasks; monitor alerts in real time.
3. View history and export alert/fault analysis.
4. Interact with multimodal AI for diagnostic insights and report generation.

------

### 🔧 Deployment & Extensibility

- Supports both local and server-side deployment.
- Flexible plugin-style integration of new models, data sources, or analysis logic.
- Ideal for smart security, power grid monitoring, and industry-specific intelligent video analytics.

------

### 🖥️ Admin Interface Highlights

- Stream Control Panel

![Control Panel](./images/control%20pannel.png)

- Multi-stream Preview

![Multi-stream Preview](./images/video%20stream%20manage.png)

- Deployment Management

![Deployment Management](./images/deployment%20manage.png)

- Algorithm Management

![Algorithm Management](./images/algorithm%20manage.png)

- Detection Task Management

![Detection Task Management](./images/video%20steam%20preview.png)

- Alert Records Page

![Alert Records Page](./images/alarm%20page.png)

- AI Interaction Interface

![Web AI](./images/ai%20chat.png)

------

### 💻 Environment Setup

| Component    | Version            |
| ------------ | ------------------ |
| Python       | 3.11               |
| Dependencies | `requirements.txt` |



#### Install & Setup

```
conda create -n your_env_name python=3.11
conda activate your_env_name
pip install -r requirements.txt
```

------

### 🚀 Startup Guide

1. **Start Admin Backend**

```
cd admin
python manage.py runserver 0.0.0.0:9001
```

1. **Launch Streaming Server (ZLMediaKit)**

```
cd zlm
# Run the ZLMediaKit executable (Linux/Windows build)
```

1. **Push Sample Video Stream**

```
cd data
# Use FFmpeg to push a video stream
```

1. **Start Detection RESTful API**

```
cd media
python app.py
```

------

### 🌟 Contribution & Notes

- If you’d like to implement your own detection algorithm, you can register it by editing the `media` folder and linking it in Django Admin.
- If you're experimenting with LLM improvements, customize the AI interface in `ai_chat_google`.
- Feel free to fork or star this repo. Raise issues or discussions if needed!

## 界面展示







- 布控管理
- ![布控管理](./images/deployment%20manage.png)
- 算法管理
- ![算法管理](./images/algorithm%20manage.png)
- 告警页面
  ![告警页面](./images/alarm%20page.png)
- Web AI
  ![Web AI](./images/ai%20chat.png)

## 结语
喜欢的可以点个star，有什么问题可以提提issue