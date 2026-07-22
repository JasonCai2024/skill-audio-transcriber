---
name: skill-audio-transcriber
description: 当用户需要从本地音频或视频文件中提取完整转录文案(TXT)或时间戳字幕文件(SRT)时使用此技能。技能会将结果自动保存为与原音视频文件同名同路径的文件。
disable-model-invocation: true
user-invocable: true
argument-hint: [audio-or-video-file-path]
---

# 音频转录与字幕提取技能 (skill-audio-transcriber)

## Goal

接收本地音频或视频文件路径，基于 ServiceHub ASR 语音识别与阿里云 OSS 临时传输能力，将音视频内容自动转录为完整 txt 文本或带精确时间戳的 srt 字幕，并严格输出在与源音视频文件相同的目录下，保持同名。

## Required Inputs

1. **媒体文件路径** (`input_path`)：绝对路径或相对路径，支持音频格式 (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, `.wma`) 或视频格式 (`.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`, `.wmv`, `.webm`)。
2. **输出类型** (`format`, 可选)：`txt` (仅文案)、`srt` (仅字幕) 或 `all` (同时输出文案和字幕，默认)。

## Workflow

1. **输入文件校验**：
   - 验证输入路径是否存在。
   - 检查后缀是否为受支持的音视频格式。
2. **环境与凭证准备**：
   - 优先从环境变量 / `.env` 加载 `SERVICEHUB_USERNAME`、`SERVICEHUB_PASSTOKEN`、阿里云 OSS AccessKey 等凭证。
   - 若未配置，自动读取 `E:\BaiduSyncdisk\LocalHub\BiSubtitles\config.json` 作为保底凭证。
3. **音频预处理（如需要）**：
   - 若输入为视频格式或非标准音频，调用 `ffmpeg` 提取单声道 16kHz WAV 临时文件。
4. **云端传输与 ASR 转录**：
   - 调用 `oss2` 将音频上传至 OSS 临时 bucket。
   - 请求 ServiceHub ASR 接口 (`https://www.ccailab.top/api/asr/paid-rotation`) 获取句级时间戳及转录全文。
   - 在 `finally` 清理逻辑中，立即删除 OSS 上的临时音频文件及本地临时 WAV 提取文件。
5. **写出目标文件**：
   - 在源文件所在同级目录下，生成同名的 `.txt` / `.srt` 文件。

## Decision Rules

- **格式判断规则**：
  - 若输入文件扩展名为 `.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`, `.wmv`, `.webm` 中的任意一种，必须先经过 FFmpeg 提取音频。
  - 若扩展名已为 `.wav`, `.mp3` 等格式，优先直接上传处理。
- **凭证降级规则**：
  - `.env` 环境变量 > `config.json` 配置文件。
- **云端资源清理规则**：
  - 无论 ASR 调用成功或失败，必须确保触发 OSS 临时文件删除逻辑。

## Output Requirements

- 生成的文件必须与输入文件**同路径、同主文件名**。
  - 例如：输入 `E:/Media/interview.mp3`，生成 `E:/Media/interview.txt` 及 `E:/Media/interview.srt`。
- TXT 文本采用 UTF-8 编码，句与句之间以换行分隔。
- SRT 字幕满足标准 SRT 语法规则 (序号、`00:00:00,000 --> 00:00:00,000` 时间轴、字幕文本、空行)。

## Validation

1. **文件存在校验**：转录完成后，检查同目录下是否生成了对应的 `.txt` 或 `.srt` 文件。
2. **非空校验**：生成的 `.txt` 或 `.srt` 文件大小必须大于 0 字节。
3. **清理校验**：确认 OSS 上的临时对象与本地临时 WAV 文件均已成功删除。

## Fallback

- 若缺乏 `ffmpeg` 运行环境：提示用户安装 FFmpeg 并加入系统环境变量 PATH。
- 若 ASR API 返回积分不足或鉴权失败：输出明确的错误提示，终止后续写盘操作。
- 若 OSS 上传失败：提示检查 `OSS_ACCESS_KEY_ID` 与 `OSS_ACCESS_KEY_SECRET`。

## Examples

### 示例 1：转录音频并同时提取 txt 和 srt
```bash
python scripts/transcribe_audio.py "E:/Recordings/meeting_20260722.mp3" --format all
```

### 示例 2：仅提取视频中的纯 txt 文案
```bash
python scripts/transcribe_audio.py "C:/Videos/presentation.mp4" --format txt
```
