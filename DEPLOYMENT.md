# Streamlit 部署指南

## 步骤 1: 部署应用

1. 访问 https://share.streamlit.io
2. 用GitHub账户登录
3. 点击 "Deploy an app"
4. 选择仓库: `chaocai1-lgtm/20260115guojifa`
5. 选择分支: `main`
6. 主文件: `gjf_graph_main.py`
7. 点击 "Deploy"

## 步骤 2: 配置环境变量（Secrets）

部署完成后，进入应用的 **Advanced settings** → **Secrets**，添加以下内容：

```
NEO4J_URI=neo4j+s://7eb127cc.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk
ADMIN_PASSWORD=admin888
```

## 步骤 3: 重新启动应用

配置完Secrets后，应用会自动重启并使用新的环境变量。

## 本地测试

在本地测试前，设置环境变量：

```bash
# Windows PowerShell
$env:NEO4J_URI="neo4j+s://7eb127cc.databases.neo4j.io"
$env:NEO4J_USERNAME="neo4j"
$env:NEO4J_PASSWORD="wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk"
$env:ADMIN_PASSWORD="admin888"

streamlit run gjf_graph_main.py
```

或者创建 `.streamlit/secrets.toml` 文件（本地开发用，不要提交到git）：

```toml
NEO4J_URI = "neo4j+s://7eb127cc.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk"
ADMIN_PASSWORD = "admin888"
```
