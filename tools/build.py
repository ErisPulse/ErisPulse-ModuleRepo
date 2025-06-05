import os
import json
from datetime import datetime
from pathlib import Path
import zipfile
import subprocess
import shutil

def run_cmd(cmd, check=True, cwd=None):
    print(f"[CMD] {cmd}")
    return subprocess.run(cmd, shell=True, check=check, cwd=cwd)

config = {
    "module_name": "YunhuAdapter",
    "github_username": "wsu2059q",  # 替换为你自己的 GitHub 用户名
    "official_repo": "ErisPulse/ErisPulse-ModuleRepo",
    "local_module_path": "YunhuAdapter",
    "files_to_include": [
        "YunhuAdapter/__init__.py",
        "YunhuAdapter/Core.py",
        "README.md"
    ]
}

# 解析仓库信息
repo_owner, repo_name = config["official_repo"].split("/")
module_repo_dir = Path(repo_name)

def is_gh_installed():
    try:
        subprocess.run("gh --version", shell=True, check=True, stdout=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

print("[INFO] 正在加载模块信息...")
init_file = Path(config["local_module_path"]) / "__init__.py"
content = init_file.read_text(encoding="utf-8")

version_line = next(line for line in content.splitlines() if '"version"' in line)
current_version = version_line.split('"')[3]

print(f"[WARN] 当前模块版本：{current_version}")

# 上次构建版本检查
last_built_version_file = Path("last_built_version.txt")
if last_built_version_file.exists():
    last_version = last_built_version_file.read_text().strip()
    if last_version == current_version:
        print("[ERROR] 当前版本与上一次构建相同，请升级版本后再继续。")
        exit(1)

print("[WARN] 注意：构建不会自动更新版本号，请确保你已手动更新版本后再继续。")
input("[ACTION] 按回车键继续...")

build_time = datetime.now().isoformat()

# 克隆官方仓库
print("[INFO] 克隆官方模块源仓库...")
module_repo_dir = Path(repo_name)

if module_repo_dir.exists():
    choice = input(f"检测到已存在的 {repo_name} 目录，是否强制删除？(y/n): ")
    if choice.lower() == 'y':
        try:
            shutil.rmtree(module_repo_dir)
        except PermissionError:
            print(f"[ERROR] 删除目录失败，权限不足，请手动删除 {repo_name} 后重试。")
            exit(1)
    else:
        print(f"[INFO] 跳过删除现有目录，将继续使用当前目录内容。")
else:
    print(f"[INFO] 正在创建新目录：{repo_name}")

run_cmd(f"git clone https://github.com/{config['official_repo']}.git {module_repo_dir}")

# 加载 map.json
print("[INFO] 加载官方 map.json...")
map_file = module_repo_dir / "map.json"
data = json.loads(map_file.read_text(encoding="utf-8"))

# 打包模块
print("[INFO] 打包模块...")
zip_name = f"{config['module_name']}-{current_version}.zip"
zip_path = Path(zip_name)
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in config["files_to_include"]:
        zipf.write(file, arcname=os.path.basename(file))

# 复制打包文件到模块源目录下的 modules/ 文件夹
print("[INFO] 复制打包文件到模块源目录...")

# 确保 modules 目录存在（现在一定存在）
modules_dir = module_repo_dir / "modules"
modules_dir.mkdir(exist_ok=True)

dest_path = modules_dir / zip_path.name
shutil.copyfile(zip_path, dest_path)

# 更新 map.json 中的模块信息
print("[INFO] 更新 map.json 中的模块信息...")
module_name = config["module_name"]
module_entry = data["modules"][module_name]

module_entry["path"] = f"/modules/{zip_name}"
module_entry["meta"]["build_time"] = build_time
module_entry["meta"]["version"] = current_version

map_file.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

# 配置 Git 提交信息
print("[INFO] 配置 Git 提交信息...")
run_cmd("git config --global user.name 'Auto Builder'", cwd=module_repo_dir)
run_cmd("git config --global user.email 'auto@builder.com'", cwd=module_repo_dir)

# 创建新分支并提交变更
print("[INFO] 创建新分支并提交变更...")
branch_name = f"update-{module_name.lower()}-{current_version}"
run_cmd(f"git checkout -b {branch_name}", cwd=module_repo_dir)
run_cmd("git add .", cwd=module_repo_dir)
run_cmd(f'git commit -m "Update {module_name} to v{current_version}"', cwd=module_repo_dir)

# 推送分支到 Fork
print("[INFO] 推送分支到你的 fork，请确保你已 fork 官方仓库...")
fork_remote = f"https://github.com/{config['github_username']}/ErisPulse-ModuleRepo.git"
run_cmd(f"git remote set-url origin {fork_remote}", cwd=module_repo_dir)
run_cmd(f"git push origin {branch_name}", cwd=module_repo_dir)

# 尝试创建 PR
print("[INFO] 即将尝试向官方仓库发起 Pull Request...")

pr_title = f"Update {module_name} to v{current_version}"
pr_body = f"更新 {module_name} 模块到版本 v{current_version}"

gh_installed = is_gh_installed()

pr_url = (
    f"https://github.com/{config['official_repo']}/compare?"
    f"expand=1&head={config['github_username']}:{branch_name}&base=main"
)

if gh_installed:
    try:
        run_cmd(
            f'gh pr create '
            f'--title "{pr_title}" '
            f'--body "{pr_body}" '
            f'--base main '
            f'--head {config["github_username"]}:{branch_name} '
            f'--repo {config["official_repo"]}',
            cwd=module_repo_dir
        )
        print(f"[SUCCESS] PR 已成功提交至官方仓库：{config['official_repo']}")
        print(f"[LINK] 查看 PR: {pr_url}")
    except subprocess.CalledProcessError:
        print("[WARN] GitHub CLI (gh) 命令执行失败，可能未登录或网络问题。")
        print("[INFO] 请访问以下链接手动创建 Pull Request：")
        print(pr_url)
else:
    print("[INFO] GitHub CLI (gh) 未安装，无法自动创建 PR。")
    print("[INFO] 请访问以下链接手动创建 Pull Request：")
    print(pr_url)

# 记录本次构建的版本
last_built_version_file = Path("last_built_version.txt")
last_built_version_file.write_text(current_version)