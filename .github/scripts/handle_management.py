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
    elif action == 'hide':
        module_info['hidden'] = True
        print(f"Hid '{module_name}' in {category}")
    elif action == 'unhide':
        module_info['hidden'] = False
        print(f"Unhid '{module_name}' in {category}")
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
