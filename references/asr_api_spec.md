# ServiceHub ASR 转录 API 规范

## 1. 接口概述

本技能基于 ServiceHub 提供的 ASR 付费轮转接口，实现高精度的音视频语音识别与逐句时间戳提取。

- **请求协议**：HTTPS POST
- **接口地址**：`https://www.ccailab.top/api/asr/paid-rotation`
- **数据格式**：`application/json`

---

## 2. 请求参数结构

```json
{
  "username": "用户账号",
  "passtoken": "密码令牌",
  "provider": "aliyun",
  "model": "paraformer-v2",
  "media_url": "https://temp-video-sub.oss-cn-chengdu.aliyuncs.com/xxx.wav",
  "deduct_points": true,
  "transcript_format": "sentence_timestamps"
}
```

### 参数说明

| 字段 | 类型 | 是否必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `username` | string | 是 | 鉴权用户名 |
| `passtoken` | string | 是 | 鉴权密码令牌 |
| `provider` | string | 否 | ASR 服务商，默认 `aliyun` |
| `model` | string | 否 | ASR 识别模型，默认 `paraformer-v2` |
| `media_url` | string | 是 | 待识别音频的公开可访问 URL (如 OSS 链接) |
| `deduct_points` | boolean| 否 | 是否扣除积分，默认 `true` |
| `transcript_format`| string | 否 | 返回格式：`plain_text` / `sentence_timestamps` / `word_timestamps` |

---

## 3. 响应数据结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "asr_task_12345678",
    "transcribed_text": "转录的完整文本内容...",
    "transcript_format": "sentence_timestamps",
    "transcript_segments": [
      {
        "text": "第一句字幕文本",
        "begin_time": 0,
        "end_time": 3500
      },
      {
        "text": "第二句字幕文本",
        "begin_time": 3500,
        "end_time": 7200
      }
    ],
    "audio_duration_seconds": 120.5,
    "processing_time": 4.2
  }
}
```
