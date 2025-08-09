> 这是一个归档文档，仅供1.x.x版本使用。
# ErisPulse - 模块源仓库

我们欢迎社区成员贡献新的模块！如果您希望提交一个新模块，请直接向本仓库提交 Pull Request。我们将在审核通过后将其合并到主分支。

## 贡献模块

请确保满足以下要求：
- 模块代码符合项目规范
- 提供完整的文档和使用说明
- 确保无版权问题，允许我们修改与发布

## 模块构建工具

我们提供自动化构建脚本 `tools/build.py`，帮助开发者快速打包发布。

### 快速部署构建工具

请运行以下命令来下载构建工具：

#### Linux / macOS:
```bash
mkdir -p tools && curl -o tools/build.py https://github.com/ErisPulse/ErisPulse-ModuleRepo/raw/main/docs/archived/tools/build.py
```

#### Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Path "tools" -ErrorAction SilentlyContinue; Invoke-WebRequest -Uri "https://github.com/ErisPulse/ErisPulse-ModuleRepo/raw/main/docs/archived/tools/build.py" -OutFile "tools/build.py"
```

### 使用方式

1. 登录 GitHub CLI（如尚未登录）：
   ```bash
   gh auth login
   ```

2. 运行构建脚本：
   ```bash
   python tools/build.py
   ```

3. 脚本会自动完成以下操作：
   - 打包模块为 ZIP 文件
   - 更新 `map.json` 中的模块信息（路径、版本、构建时间）
   - 推送变更到你的 Fork
   - 向官方仓库发起 PR（需已登录 GitHub CLI）

---

## 感谢您的支持与贡献！
