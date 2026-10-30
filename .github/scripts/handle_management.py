#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模块管理：支持单条或批量（items 数组）。

payload 形态：
  单条  {action, name, type, uid, edit_data}
  批量  {items: [{action, name, type, uid, edit_data}, ...]}

批量中单条失败不中断其它条目；全部失败才以非零退出码结束。
"""

import json
import os
import sys
from datetime import datetime, timezone

from packages_lib import normalize_category, normalize_i18n, normalize_tags, write_packages

CATEGORY_MAP = {'module': 'modules', 'adapter': 'adapters'}


def parse_json_field(value, fallback):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return fallback
    return value if value is not None else fallback


def apply_item(packages, item):
    """应用单条操作，返回 (ok, message)。"""
    action = item.get('action')
    module_name = item.get('name')
    module_type = item.get('type', 'module')
    # 归属身份：uids（工作台传用户全部身份：github:<id> / wb:<uid> …），兼容旧的单 uid；
    # staff=1 表示管理员操作（工作台端已做角色校验），跳过所有权校验直接放行
    uids = item.get('uids') or ([item['uid']] if item.get('uid') else [])
    if isinstance(uids, str):
        uids = [uids]
    staff = bool(item.get('staff'))

    if not action or not module_name:
        return False, 'Missing action or name'

    category = CATEGORY_MAP.get(module_type, 'modules')
    if category not in packages or module_name not in packages[category]:
        return False, f"Module '{module_name}' not found in {category}"

    module_info = packages[category][module_name]

    existing_uid = module_info.get('submitted_by_uid', '')
    if uids and existing_uid and existing_uid not in uids and not staff:
        return False, f"Ownership verification failed for '{module_name}'"
    if uids and not existing_uid:
        # legacy 条目无归属记录：自动创建并归操作方（认领式接管；管理员操作同样补齐归属）
        module_info['submitted_by_uid'] = uids[0]
        print(f"Claimed ownership of '{module_name}' -> {uids[0]}")

    if action == 'delete':
        del packages[category][module_name]
        return True, f"Deleted '{module_name}' from {category}"

    if action != 'edit':
        return False, f"Unknown action: {action}"

    edit_data = parse_json_field(item.get('edit_data', '{}'), {})
    if not isinstance(edit_data, dict):
        edit_data = {}

    submitter_info = parse_json_field(edit_data.get('submitter', '{}'), {})
    if not isinstance(submitter_info, dict):
        submitter_info = {}

    # 标签：显式提交（即使清空为空列表）即整体替换，未提交视为不改动
    tags_raw = edit_data.get('tags', None)
    if tags_raw is not None:
        tags = parse_json_field(tags_raw, [])
        module_info['tags'] = normalize_tags(tags if isinstance(tags, (list, tuple)) else [])

    # 界面语言：同 tags 的 provided 语义
    i18n_raw = edit_data.get('i18n', None)
    if i18n_raw is not None:
        i18n = parse_json_field(i18n_raw, [])
        module_info['i18n'] = normalize_i18n(i18n if isinstance(i18n, (list, tuple)) else [])

    if edit_data.get('package'):
        module_info['package'] = edit_data['package']
    if edit_data.get('description'):
        module_info['description'] = edit_data['description']
    if edit_data.get('author'):
        module_info['author'] = edit_data['author']
    if edit_data.get('repository'):
        module_info['repository'] = edit_data['repository']
    if edit_data.get('version') and edit_data['version'] != '0.0.0':
        module_info['version'] = edit_data['version']

    # 分类：受控字段，非法值忽略（提交入口 Worker 已先行校验）
    category_id = normalize_category(edit_data.get('category'))
    if category_id is not None:
        module_info['category'] = category_id

    if edit_data.get('min_sdk_version'):
        module_info['min_sdk_version'] = edit_data['min_sdk_version']
    elif 'min_sdk_version' in module_info:
        del module_info['min_sdk_version']

    # logo：https URL 或 data:image URL（≤100KB）；空字符串 = 移除
    if 'logo' in edit_data:
        logo_val = str(edit_data['logo'] or '')
        if logo_val:
            if not (logo_val.startswith('https://') or logo_val.startswith('data:image/')):
                return False, f"Invalid logo for '{module_name}': {logo_val[:60]!r}"
            if logo_val.startswith('data:image/') and len(logo_val) > 140 * 1024:
                return False, f"Logo data URL too large for '{module_name}' (>100KB)"
            module_info['logo'] = logo_val
        else:
            module_info.pop('logo', None)

    # 验证状态：仅显式提交时改动。true/false 都显式落盘——
    # 字段缺失视为隐式已验证（legacy 模块），显式 false 才是未验证
    if 'verified' in edit_data:
        module_info['verified'] = bool(edit_data['verified'])

    if submitter_info:
        module_info['submitted_by'] = submitter_info.get('name', module_info.get('submitted_by', ''))
        module_info['submitted_by_uid'] = submitter_info.get('uid', module_info.get('submitted_by_uid', ''))
        module_info['oauth_provider'] = submitter_info.get('provider', module_info.get('oauth_provider', ''))

    return True, f"Edited '{module_name}' in {category}"


def handle_management():
    payload_json = os.environ.get('MANAGEMENT_DATA')
    if not payload_json:
        print("No MANAGEMENT_DATA environment variable found")
        sys.exit(1)

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in MANAGEMENT_DATA: {e}")
        sys.exit(1)

    items = payload.get('items')
    if not isinstance(items, list):
        items = [payload]
    if not items:
        print("Empty items")
        sys.exit(1)

    try:
        with open('packages.json', 'r', encoding='utf-8') as f:
            packages = json.load(f)
    except Exception as e:
        print(f"Cannot read packages.json: {e}")
        sys.exit(1)

    ok_count = 0
    failed = []
    for item in items:
        if not isinstance(item, dict):
            failed.append('non-object item')
            continue
        ok, message = apply_item(packages, item)
        print(message)
        if ok:
            ok_count += 1
        else:
            failed.append(message)

    if ok_count == 0:
        print(f"All {len(items)} operation(s) failed")
        sys.exit(1)

    packages['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        # 统一经 packages_lib 落盘：编辑后仍保持排序与字段顺序稳定
        write_packages('packages.json', packages)
    except Exception as e:
        print(f"Cannot write packages.json: {e}")
        sys.exit(1)

    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"applied={ok_count}\nfailed={len(failed)}\n")
    if failed:
        print(f"Partial failure: {len(failed)} of {len(items)}")


if __name__ == '__main__':
    handle_management()
