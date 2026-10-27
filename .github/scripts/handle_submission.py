#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

from packages_lib import (
    CATEGORY_IDS,
    normalize_category,
    normalize_i18n,
    normalize_tags,
    write_packages,
)


def check_pypi_exists(package_name):
    if requests is None:
        print(f"WARNING: requests not available, skipping PyPI check for {package_name}")
        return True

    try:
        resp = requests.get(f'https://pypi.org/pypi/{package_name}/json', timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            version = data['info'].get('version', '0.0.0')
            print(f"PyPI package '{package_name}' found, version: {version}")
            return True
        else:
            print(f"PyPI package '{package_name}' NOT found (HTTP {resp.status_code})")
            return False
    except Exception as e:
        print(f"PyPI check error for {package_name}: {e}")
        return False


def validate_submission(data):
    required_fields = ['name', 'package', 'description', 'author', 'repository']
    for field in required_fields:
        if not data.get(field):
            print(f"Missing required field: {field}")
            return False, f"Missing required field: {field}"

    if not re.match(r'^[a-zA-Z0-9_-]+$', data['name']):
        print(f"Invalid module name: {data['name']}")
        return False, f"Invalid module name format: {data['name']}"

    if not re.match(r'^[a-zA-Z0-9_.-]+$', data['package']):
        print(f"Invalid package name: {data['package']}")
        return False, f"Invalid package name format: {data['package']}"

    repo = data.get('repository', '')
    if not (repo.startswith('https://github.com/') or repo.startswith('https://codeberg.org/')):
        print(f"Invalid repository URL: {repo}")
        return False, f"Invalid repository URL: {repo}"

    if len(data.get('description', '')) < 10:
        print("Description too short (minimum 10 characters)")
        return False, "Description too short (minimum 10 characters)"

    # 标签：自由文本，不限制内容 —— 作者可以用中文或英文表达，仓库侧也不做
    # 词表匹配；这里只做卫生处理，字符规则（长度、允许字符）由提交入口把关
    tags = data.get('tags', [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            print(f"Invalid tags payload: {data.get('tags')!r}")
            return False, "Invalid tags payload."
    if not isinstance(tags, (list, tuple)):
        print(f"Invalid tags payload: {data.get('tags')!r}")
        return False, "Invalid tags payload."
    data['tags'] = normalize_tags(tags)

    # 界面语言：结构化受控字段，格式不合法的代码直接拒绝（与卫生处理不同，
    # 这里是提交入口，拒绝比静默丢弃更能让作者发现问题）
    i18n = data.get('i18n', [])
    if isinstance(i18n, str):
        try:
            i18n = json.loads(i18n)
        except (json.JSONDecodeError, TypeError):
            print(f"Invalid i18n payload: {data.get('i18n')!r}")
            return False, "Invalid i18n payload."
    if not isinstance(i18n, (list, tuple)):
        print(f"Invalid i18n payload: {data.get('i18n')!r}")
        return False, "Invalid i18n payload."
    data['i18n'] = normalize_i18n(i18n)

    # 分类：受控字段（编号），与自由标签相反 —— 必须落在词表内
    raw_category = data.get('category')
    category_id = normalize_category(raw_category)
    if category_id is None:
        print(f"Missing or invalid category: {raw_category!r}")
        return False, (
            "Missing or invalid category: {0!r}. Expected one of {1}.".format(
                raw_category, list(CATEGORY_IDS)
            )
        )
    data['category'] = category_id

    # logo：可选。https URL 或 data:image URL（解码后 ≤100KB；后续提交脚本将自动压缩）
    logo = data.get('logo', '')
    if logo:
        if not (str(logo).startswith('https://') or str(logo).startswith('data:image/')):
            print(f"Invalid logo: {str(logo)[:60]!r}")
            return False, "Invalid logo: expected an https URL or data:image URL (<=100KB)."
        if str(logo).startswith('data:image/') and len(str(logo)) > 140 * 1024:
            return False, "Logo data URL too large (>100KB)."

    if not check_pypi_exists(data['package']):
        print(f"Package '{data['package']}' not found on PyPI. Module must be published to PyPI first.")
        return False, f"Package '{data['package']}' not found on PyPI. Please publish your package to PyPI before submitting."

    return True, None


def handle_submission():
    submission_json = os.environ.get('SUBMISSION_DATA')
    if not submission_json:
        print("No SUBMISSION_DATA environment variable found")
        sys.exit(1)

    try:
        submission = json.loads(submission_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in SUBMISSION_DATA: {e}")
        sys.exit(1)

    # 兼容打包载荷：GitHub dispatch 的 client_payload 最多 10 个属性，
    # Worker 把 min_sdk_version / category / i18n 统一打包进 data（JSON 字符串）；
    # 旧版平铺字段仍然可读（直接覆盖到顶层后走原校验流程）
    data_raw = submission.get('data', '{}')
    try:
        data_extra = json.loads(data_raw) if isinstance(data_raw, str) else (data_raw or {})
    except (json.JSONDecodeError, TypeError):
        print(f"Invalid data payload: {data_raw!r}")
        sys.exit(1)
    for key in ('min_sdk_version', 'category', 'tags', 'i18n'):
        if key in data_extra and data_extra[key] is not None:
            submission[key] = data_extra[key]

    valid, error_msg = validate_submission(submission)
    if not valid:
        print(f"Validation failed: {error_msg}")
        with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
            f.write(f"error_message={error_msg}\n")
        sys.exit(1)

    try:
        with open('packages.json', 'r', encoding='utf-8') as f:
            packages = json.load(f)
    except Exception as e:
        print(f"Cannot read packages.json: {e}")
        sys.exit(1)

    submit_type = submission.get('type', 'module')
    # 注意：container 是索引容器（modules / adapters），
    # 与条目的 category（分类编号，1..7）是两个不同的概念
    container_map = {
        'module': 'modules',
        'adapter': 'adapters'
    }
    container = container_map.get(submit_type, 'modules')

    if container not in packages:
        print(f"Container '{container}' not found in packages.json")
        sys.exit(1)

    module_name = submission['name']

    for container_name in ('modules', 'adapters'):
        if module_name in packages.get(container_name, {}):
            print(f"Module '{module_name}' already exists in {container_name}")
            with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
                f.write(f"error_message=Module '{module_name}' already exists\n")
            sys.exit(1)

    submitter_raw = submission.get('submitter', '{}')
    try:
        submitter_info = json.loads(submitter_raw) if isinstance(submitter_raw, str) else submitter_raw
    except (json.JSONDecodeError, TypeError):
        submitter_info = {}
    submitted_by = submitter_info.get('name', '')
    submitted_by_uid = submitter_info.get('uid', '')
    oauth_provider = submitter_info.get('provider', '')

    # 标签与分类已在 validate_submission 中归一化/校验，这里保持幂等
    tags = normalize_tags(submission.get('tags') or [])
    category_id = normalize_category(submission.get('category'))
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    user_daily_count = 0
    for container_name in ('modules', 'adapters'):
        for name, info in packages.get(container_name, {}).items():
            submitted_at = info.get('submitted_at', '')
            if not submitted_at or not submitted_at.startswith(today):
                continue
            if submitted_by_uid and info.get('submitted_by_uid', '') == submitted_by_uid:
                user_daily_count += 1
            elif not submitted_by_uid and info.get('submitted_by', '') == submitted_by:
                user_daily_count += 1

    if user_daily_count >= 3:
        error_msg = f"User '{submitted_by}' has already submitted {user_daily_count} modules today. Daily limit is 3."
        print(error_msg)
        with open(os.environ.get('GITHUB_OUTPUT', 'a'), 'a') as f:
            f.write(f"error_message={error_msg}\n")
        sys.exit(1)

    pypi_version = submission.get('version', '0.0.0') or '0.0.0'
    if pypi_version == '0.0.0' and requests:
        try:
            resp = requests.get(f'https://pypi.org/pypi/{submission["package"]}/json', timeout=15)
            if resp.status_code == 200:
                pypi_version = resp.json()['info'].get('version', '0.0.0')
        except Exception:
            pass

    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    entry = {
        'package': submission['package'],
        'version': pypi_version,
        'author': submission['author'],
        'description': submission['description'],
        'repository': submission['repository'],
        'official': False,
        'verified': False,
        'submitted_by': submitted_by,
        'submitted_by_uid': submitted_by_uid,
        'oauth_provider': oauth_provider,
        'submitted_at': current_time,
        'category': category_id,
        'tags': tags,
        'i18n': normalize_i18n(submission.get('i18n') or [])
    }

    if submit_type != 'adapter' and submission.get('min_sdk_version'):
        entry['min_sdk_version'] = submission['min_sdk_version']

    if submission.get('logo'):
        entry['logo'] = submission['logo']

    packages[container][module_name] = entry

    packages['last_updated'] = current_time

    try:
        # 统一经 packages_lib 落盘：新条目自动落到排序位置，字段顺序规范化
        write_packages('packages.json', packages)
    except Exception as e:
        print(f"Cannot write packages.json: {e}")
        sys.exit(1)

    print(f"Successfully added '{module_name}' to {container} (version {pypi_version})")
    print(f"verified: false, submitted_by: {submitted_by}")

    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"module_name={module_name}\n")


if __name__ == '__main__':
    handle_submission()
