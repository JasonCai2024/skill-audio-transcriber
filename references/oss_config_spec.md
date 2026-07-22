# ServiceHub OSS 代理服务 API 规范

## 1. 概述

本技能无需客户端配置任何阿里云 AccessKey、Secret 或 Bucket。技能在运行过程中，统一调用 ServiceHub 服务端提供的 OSS 代理接口，实现音视频文件的安全临时上传与删除。

---

## 2. 接口端点规范

所有请求均发送至 ServiceHub 服务器（默认：`https://www.ccailab.top`）。

### 2.1 音频代理上传

- **请求路径**：`POST /api/oss/upload-audio`
- **请求格式**：`multipart/form-data`
- **表单字段**：
  - `username` (string): ServiceHub 用户账号
  - `passtoken` (string): ServiceHub 密码令牌
  - `audio_file` (file): 音频文件内容（支持 `.mp3`, `.wav`, `.m4a`）
  - `filename` (string, 可选): 自定义文件名
- **响应示例**：
  ```json
  {
    "success": true,
    "message": "音频上传成功",
    "data": {
      "oss_url": "https://temp-video-sub.oss-cn-chengdu.aliyuncs.com/jianying-auto/audio_123.wav",
      "object_name": "jianying-auto/audio_123.wav"
    },
    "timestamp": "2026-07-22 21:00:00"
  }
  ```

---

### 2.2 音频代理删除

- **请求路径**：`POST /api/oss/delete-audio`
- **请求格式**：`application/json`
- **Payload 示例**：
  ```json
  {
    "username": "用户账号",
    "passtoken": "密码令牌",
    "oss_url": "https://temp-video-sub.oss-cn-chengdu.aliyuncs.com/jianying-auto/audio_123.wav"
  }
  ```
- **响应示例**：
  ```json
  {
    "success": true,
    "message": "音频删除成功",
    "data": {
      "oss_url": "https://...",
      "deleted": true,
      "object_name": "jianying-auto/audio_123.wav"
    },
    "timestamp": "2026-07-22 21:00:05"
  }
  ```

---

## 3. 安全与隔离设计

1. **零密钥残留**：客户端仅需保存 ServiceHub 用户名与密码，无需暴露或保留阿里云基础设施管理密钥。
2. **服务端鉴权**：ServiceHub 服务端自动校验账号合法性并统一调度私有云存储桶。
3. **即用即销**：ASR 转录任务完成后，客户端自动触发删除请求，清空中间文件。
