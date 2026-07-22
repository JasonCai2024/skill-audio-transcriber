# 阿里云 OSS 存储配置规范

## 1. 概述

阿里云 OSS 用于临时存放本地转录音视频文件，生成可供 ASR API 访问的公开 URL。

---

## 2. 凭证配置

支持从环境变量与 `.env` 中装载：

```ini
OSS_BUCKET_NAME=temp-video-sub
OSS_ACCESS_KEY_ID=LTAI5tCAgUX...
OSS_ACCESS_KEY_SECRET=s5MhQ27vh...
OSS_REGION=oss-cn-chengdu
```

---

## 3. 生命周期与物理隔离

1. **命名规范**：文件上传时使用 `YYYYMMDDHHmmss_<原文件名>` 作为 Object Key，避免路径碰撞。
2. **及时清理**：脚本在转录成功或捕获异常后，均在 `finally` 块中立即调用 `delete_object` 删除 OSS 临时文件。
3. **敏感凭证防泄漏**：禁止将真实的 AccessKeyID 与 Secret 提交至 Git 仓库。
