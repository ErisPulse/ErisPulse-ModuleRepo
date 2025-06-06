import os
import json
from datetime import datetime
from pathlib import Path
import zipfile
import subprocess
import shutil
import hashlib

config = {
    "module_name": "YourModuleName",                   # 模块名称
    "github_username": "your_github_username",         # 你的 GitHub 用户名
    "official_repo": "ErisPulse/ErisPulse-ModuleRepo", # 官方仓库地址（一般无需更改）
    "local_module_path": "YourModuleName",             # 本地模块文件夹路径
    "files_to_include": [                              # 需要包含的文件列表
        "YourModuleName/__init__.py",
        "YourModuleName/Core.py",
        "README.md"
    ]
}

def run_cmd(cmd, check=True, cwd=None):
    print(f"[CMD] {cmd}")
    return subprocess.run(cmd, shell=True, check=check, cwd=cwd)


def calculate_file_hash(file_path, hash_algorithm="sha256"):
    hash_func = getattr(hashlib, hash_algorithm)()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def on_rm_error(func, path, exc_info):
    os.chmod(path, 0o777)
    func(path)

def is_gh_installed():
    try:
        subprocess.run("gh --version", shell=True, check=True, stdout=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def ensure_fork(repo):
    username = config["github_username"]
    fork_repo = f"{username}/{repo.split('/')[-1]}"

    try:
        run_cmd(f"gh repo view {fork_repo}", check=True)
        print(f"[INFO] 已找到 fork 的仓库：{fork_repo}")
    except subprocess.CalledProcessError:
        print(f"[INFO] 正在为你 fork 官方仓库：{repo}")
        run_cmd(f"gh repo fork {repo} --clone=false")

repo_owner, repo_name = config["official_repo"].split("/")
module_repo_dir = Path(repo_name)

# 确保 gh 安装
if not is_gh_installed():
    print("""
[ERROR] GitHub CLI (gh) 未安装。

请先安装 gh：
Windows: https://github.com/cli/cli/releases/latest
Linux: sudo apt install gh
macOS: brew install gh

安装完成后重新运行此脚本。
""")
    exit(1)

print("[INFO] 正在加载模块信息...")
init_file = Path(config["local_module_path"]) / "__init__.py"
content = init_file.read_text(encoding="utf-8")

# 提取 meta JSON 块
meta_start = content.find("{")
meta_end = content.rfind("}") + 1
if meta_start == -1 or meta_end == -1:
    print("[ERROR] 未找到模块元信息，请确保 __init__.py 中有正确的 JSON 块定义。")
    exit(1)

try:
    module_meta = json.loads(content[meta_start:meta_end])
except json.JSONDecodeError as e:
    print(f"[ERROR] 模块元信息 JSON 格式错误：{e}")
    exit(1)

current_version = module_meta.get("meta", {}).get("version")
if not current_version:
    print("[ERROR] 未找到版本号，请确保 __init__.py 中有 'version' 字段。")
    exit(1)

# 构建前先打包一次，用于计算当前内容哈希
temp_zip = Path("temp_build.zip")
with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in config["files_to_include"]:
        zipf.write(file, arcname=os.path.basename(file))

current_build_hash = calculate_file_hash(temp_zip)

# 检查是否已有 build_hash 注释
content_lines = content.splitlines()
try:
    build_hash_line = next(line for line in content_lines if line.startswith("# build_hash="))
    last_build_hash = build_hash_line.split('"')[1]
    if last_build_hash == current_build_hash:
        print("[ERROR] 当前构建内容与上一次一致，请修改模块内容后再继续。")
        exit(1)
except StopIteration:
    pass

print(f"[WARN] 当前模块版本：{current_version}")
print("[WARN] 注意：构建不会自动更新版本号，请确保你已手动更新版本后再继续。")
input("[ACTION] 按回车键继续...")

build_time = datetime.now().isoformat()

# Fork 并克隆仓库
fork_repo = f"{config['github_username']}/{repo_name}"
ensure_fork(config["official_repo"])

print("[INFO] 克隆官方模块源仓库...")
module_repo_dir = Path(repo_name)

if module_repo_dir.exists():
    choice = input(f"检测到已存在的 {repo_name} 目录，是否强制删除？(y/n): ")
    if choice.lower() == 'y':
        print(f"[INFO] 正在强制删除目录：{repo_name}")
        try:
            shutil.rmtree(module_repo_dir, onerror=on_rm_error)
        except Exception as e:
            print(f"[ERROR] 删除目录失败（即使尝试强制删除）：{e}")
            exit(1)
    else:
        print(f"[INFO] 跳过删除现有目录，将继续使用当前目录内容。")
else:
    print(f"[INFO] 正在创建新目录：{repo_name}")

run_cmd(f"gh repo clone {fork_repo} {module_repo_dir}")

# 加载 map.json
print("[INFO] 加载官方 map.json...")
map_file = module_repo_dir / "map.json"
data = json.loads(map_file.read_text(encoding="utf-8"))

# 构造模块条目（修复了嵌套结构）
module_name = config["module_name"]
module_entry = {
    "path": f"/{module_name}-{current_version}.zip",
    "meta": {
        "name": module_meta.get("meta", {}).get("name"),
        "version": module_meta.get("meta", {}).get("version"),
        "description": module_meta.get("meta", {}).get("description"),
        "author": module_meta.get("meta", {}).get("author"),
        "license": module_meta.get("meta", {}).get("license"),
        "homepage": module_meta.get("meta", {}).get("homepage")
    },
    "dependencies": module_meta.get("dependencies", {}),
    "build_time": build_time
}

# 替换或新增模块信息
data["modules"][module_name] = module_entry

# 写入 map.json
map_file.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

# 打包模块
print("[INFO] 打包模块...")
zip_name = f"{config['module_name']}-{current_version}.zip"
zip_path = Path(zip_name)
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in config["files_to_include"]:
        zipf.write(file, arcname=os.path.basename(file))

# 复制文件
modules_dir = module_repo_dir / "modules"
modules_dir.mkdir(exist_ok=True)
dest_path = modules_dir / zip_path.name
shutil.copyfile(zip_path, dest_path)

# 配置 Git 用户
run_cmd("gh config set git_protocol ssh", cwd=module_repo_dir)

# 检查并暂存本地改动
try:
    print("[INFO] 检测并暂存本地未提交改动...")
    run_cmd("git stash --all", cwd=module_repo_dir)
except subprocess.CalledProcessError:
    print("[WARN] 没有需要暂存的改动或暂存失败，继续执行...")

# 同步主分支
print("[INFO] 正在同步远程 main 分支...")
run_cmd("gh repo sync -b main", cwd=module_repo_dir)

# 恢复暂存的改动
try:
    print("[INFO] 恢复暂存的本地改动...")
    run_cmd("git stash pop", cwd=module_repo_dir)
except subprocess.CalledProcessError:
    print("[WARN] 没有暂存内容或恢复失败，跳过。")

# 创建并推送新分支
branch_name = f"update-{module_name.lower()}-{current_version}"
print(f"[INFO] 创建并推送新分支: {branch_name}")
run_cmd(f"git checkout -b {branch_name}", cwd=module_repo_dir)
run_cmd(f"git add .", cwd=module_repo_dir)
run_cmd(f'git commit -m "Update {module_name} to v{current_version}"', cwd=module_repo_dir)
run_cmd(f"git push origin {branch_name}", cwd=module_repo_dir)

# 设置默认仓库
run_cmd("gh repo set-default", cwd=module_repo_dir)

# 创建 PR
print("[INFO] 正在创建 Pull Request...")
run_cmd([
    "gh", "pr", "create",
    "--title", f"Update {module_name} to v{current_version}",
    "--body", f"添加/更新 `{module_name}` 模块至 v{current_version}",
    "--base", "main",
    "--head", branch_name
], cwd=module_repo_dir)

# 写入 build_hash 到 __init__.py
build_hash = calculate_file_hash(zip_path)
with open(init_file, "a", encoding="utf-8") as f:
    f.write(f'\n# build_hash="{build_hash}"\n')

print("[INFO] 构建完成！")
