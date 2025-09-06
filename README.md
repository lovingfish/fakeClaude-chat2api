# TalkAI OpenAI API 适配器

这是一个将 TalkAI 的 API 格式转换为 OpenAI ChatCompletion API 格式的适配器。
它允许您在任何兼容 OpenAI API 的客户端中使用 TalkAI 支持的各种模型。

## 功能

- 兼容 OpenAI Chat API (`/v1/chat/completions`) 和模型列表 API (`/v1/models`)。
- 支持流式 (streaming) 和非流式响应。
- 通过 API 密钥进行简单的 Bearer Token 认证。
- 优先从环境变量 `CLIENT_API_KEYS` 读取密钥，方便部署；如果环境变量不存在，则回退到 `client_api_keys.json` 文件，方便本地开发。
- 支持处理多部分内容（`multipart content`），兼容新版客户端格式。

## 部署指南

您可以将此应用轻松部署到 Vercel 或 Render 等 Serverless 平台上。

### 准备工作

1.  将本项目 Fork 到您自己的 GitHub 账户。
2.  确保您的代码仓库中包含 `main.py` 和 `requirements.txt` 文件。

---

### 部署到 Vercel

Vercel 是部署此类 Web 应用的绝佳选择，因为它对 FastAPI 有很好的支持。

1.  **登录 Vercel**: 使用您的 GitHub 帐户登录 [Vercel](https://vercel.com/)。
2.  **导入项目**:
    *   在 Vercel Dashboard 中，点击 "Add New..." -> "Project"。
    *   选择您刚刚 Fork 的 GitHub 仓库，点击 "Import"。
3.  **配置项目**:
    *   **Framework Preset**: Vercel 应该会自动识别为 "FastAPI"。如果没有，请手动选择它。
    *   **Root Directory**: 保持默认即可。
4.  **添加环境变量**:
    *   展开 "Environment Variables" 部分。
    *   添加一个新的环境变量：
        *   **Name**: `CLIENT_API_KEYS`
        *   **Value**: `<YOUR_SECRET_KEY>` (您可以设置一个或多个密钥，用逗号分隔，例如 `<YOUR_SECRET_KEY>,another-key`)
5.  **部署**:
    *   点击 "Deploy" 按钮。
    *   Vercel 将会自动构建和部署您的应用。稍等片刻，部署就会完成。

部署成功后，Vercel 会提供给您一个域名 (例如 `your-project-name.vercel.app`)，这就是您的 API 地址。

---

### 部署到 Render

Render 是另一个优秀的免费部署平台。

1.  **登录 Render**: 使用您的 GitHub 帐户登录 [Render](https://render.com/)。
2.  **创建新服务**:
    *   在 Render Dashboard 中，点击 "New +" -> "Web Service"。
    *   连接您的 GitHub 账户并选择您的仓库。
3.  **配置服务**:
    *   **Name**: 给您的服务起一个名字 (例如 `talkai-adapter`)。
    *   **Region**: 选择一个离您近的区域。
    *   **Branch**: 选择 `main` 或您的主分支。
    *   **Root Directory**: 留空。
    *   **Runtime**: 选择 "Python 3"。
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4.  **添加环境变量**:
    *   在配置页面的 "Advanced" 部分，找到 "Environment Variables"。
    *   点击 "Add Environment Variable"。
        *   **Key**: `CLIENT_API_KEYS`
        *   **Value**: `<YOUR_SECRET_KEY>`
5.  **创建服务**:
    *   选择一个免费实例类型 (Free instance type)。
    *   点击 "Create Web Service" 按钮。
    *   Render 会开始构建和部署您的应用。

部署完成后，Render 会在页面顶部显示您的服务地址 (例如 `https://your-service-name.onrender.com`)。

## 如何使用

部署完成后，您就可以像调用 OpenAI API 一样调用您的服务了。

将下面的 `<YOUR_DEPLOYED_URL>` 替换为您在 Vercel 或 Render 上获得的地址。

```bash
curl <YOUR_DEPLOYED_URL>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_SECRET_KEY>" \
  -d '{
    "model": "Claude Sonnet 4.1",
    "messages": [
      {
        "role": "user",
        "content": "你好，请介绍一下你自己"
      }
    ]
  }'
```

现在您可以把代码推送到远程仓库，然后按照上面的指南进行部署了。
