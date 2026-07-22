# 技能安装与环境配置指南 (`INSTALL.md`)

## 1. 前置依赖

在运行本技能前，请确保系统中已准备好以下环境：

### Python 环境
- Python 3.8 或更高版本。

### FFmpeg 工具
- 脚本需要 `ffmpeg` 来处理视频提取与音频采样率转换。
- **Windows 安装**：使用 `winget install Gyan.FFmpeg` 或手动下载解压并添加 `bin` 目录至系统 PATH。
- **验证安装**：在终端中运行 `ffmpeg -version`，应能正常显示版本信息。

---

## 2. 安装步骤

1. 安装 Python 依赖扩展包：
   ```bash
   pip install -r scripts/requirements.txt
   ```

2. 凭证配置（推荐）：
   复制 `.env.example` 模板并重命名为 `.env`：
   ```bash
   cp .env.example .env
   ```
   编辑 `.env` 文件，填写 ServiceHub 用户凭证与阿里云 OSS AccessKey。

---

## 3. 常见问题排查

- **提示 `FFmpeg non-existent on system PATH`**：说明系统缺少 `ffmpeg` 命令，请检查环境变量配置。
- **提示 `ASR API Error`**：请检查用户名与密码令牌是否正确，或账号积分是否足够。
- **提示 `OSS credentials missing`**：请检查 `.env` 文件或配置中的 AccessKeyID 和 AccessKeySecret 是否有效。
