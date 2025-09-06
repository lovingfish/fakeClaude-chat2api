# TalkAI OpenAI API 适配器

这是一个将 TalkAI 的 API 格式转换为 OpenAI ChatCompletion API 格式的适配器。

## 功能

- 兼容 OpenAI Chat API (`/v1/chat/completions`) 和模型列表 API (`/v1/models`)。
- 支持流式 (streaming) 和非流式响应。
- 通过 API 密钥进行简单的 Bearer Token 认证。
- 优先从环境变量 `PASSWORD` 读取服务认证密钥；如果环境变量不存在，则回退到 `client_api_keys.json` 文件以便本地开发。
- 支持处理多部分内容（`multipart content`），兼容新版客户端格式。

## 部署到 Render（推荐）

Render 更适合长期运行的 Python/uvicorn 服务，部署简单且稳定。

1. 在 Render 注册并登录（使用 GitHub 登录）。
2. 点击 "New +" → "Web Service"，连接您的 GitHub 仓库并选择本项目。
3. 配置服务：
   - Name: 选一个名字（例如 `talkai-adapter`）。
   - Region: 选择离您近的区域。
   - Branch: 选择 `main`。
   - Runtime: 选择 `Python 3`。
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. 在 Environment Variables 中添加：
   - Key: `PASSWORD`
   - Value: `<YOUR_SERVICE_SECRET_KEY>`（用于保护您部署的服务，示例：`.....zhu`）
5. 创建服务，Render 会自动构建并部署您的应用。

部署完成后，Render 会给出服务地址（例如 `https://your-service-name.onrender.com`）。

## 调用示例

把 `<YOUR_DEPLOYED_URL>` 替换为您在 Render 上获得的地址：

```bash
curl <YOUR_DEPLOYED_URL>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_SERVICE_SECRET_KEY>" \
  -d '{
    "model": "Claude Sonnet 4.1",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
  }'
```

## 下游服务密钥（TalkAI）

程序会从 `client_api_keys.json` 中读取用于请求 `claude.talkai.info` 的密钥（字段示例：`["sk-talkai-..."]`）。

本地测试：保留或编辑 `client_api_keys.json`；生产环境请不要提交真实密钥到仓库，Render 的 `PASSWORD` 环境变量用于保护对外请求。
