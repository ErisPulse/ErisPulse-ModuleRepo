#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from datetime import datetime, timezone


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

    action = payload.get('action')
    module_name = payload.get('name')
    module_type = payload.get('type', 'module')
    uid = payload.get('uid', '')

    if not action or not module_name:
        print("Missing action or name")
        sys.exit(1)

    category_map = {'module': 'modules', 'adapter': 'adapters'}
    category = category_map.get(module_type, 'modules')

    try:
        with open('packages.json', 'r', encoding='utf-8') as f:
            packages = json.load(f)
    except Exception as e:
        print(f"Cannot read packages.json: {e}")
        sys.exit(1)

    if category not in packages or module_name not in packages[category]:
        print(f"Module '{module_name}' not found in {category}")
        sys.exit(1)

    module_info = packages[category][module_name]

    if uid and module_info.get('submitted_by_uid', '') != uid:
        print(f"Ownership verification failed: uid mismatch")
        sys.exit(1)

    if action == 'delete':
        del packages[category][module_name]
        print(f"Deleted '{module_name}' from {category}")
    elif action == 'edit':
        edit_raw = payload.get('edit_data', '{}')
        try:
            edit_data = json.loads(edit_raw) if isinstance(edit_raw, str) else edit_raw
        except (json.JSONDecodeError, TypeError):
            edit_data = {}

        submitter_raw = edit_data.get('submitter', '{}')
        try:
            submitter_info = json.loads(submitter_raw) if isinstance(submitter_raw, str) else submitter_raw
        except (json.JSONDecodeError, TypeError):
            submitter_info = {}

        tags_raw = edit_data.get('tags', '[]')
        try:
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        except (json.JSONDecodeError, TypeError):
            tags = []

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
        if tags:
            module_info['tags'] = tags

        if edit_data.get('min_sdk_version'):
            module_info['min_sdk_version'] = edit_data['min_sdk_version']
        elif 'min_sdk_version' in module_info:
            del module_info['min_sdk_version']

        if submitter_info:
            module_info['submitted_by'] = submitter_info.get('name', module_info.get('submitted_by', ''))
            module_info['submitted_by_uid'] = submitter_info.get('uid', module_info.get('submitted_by_uid', ''))
            module_info['oauth_provider'] = submitter_info.get('provider', module_info.get('oauth_provider', ''))

        print(f"Edited '{module_name}' in {category}")
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    packages['last_updated'] = current_time

    try:
        with open('packages.json', 'w', encoding='utf-8') as f:
            json.dump(packages, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Cannot write packages.json: {e}")
        sys.exit(1)

    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"module_name={module_name}\naction={action}\n")


if __name__ == '__main__':
    handle_management()
