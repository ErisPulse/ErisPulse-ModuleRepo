#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timezone


def validate_submission(data):
    required_fields = ['name', 'package', 'description', 'author', 'repository']
    for field in required_fields:
        if not data.get(field):
            print(f"Missing required field: {field}")
            return False

    if not re.match(r'^[a-zA-Z0-9_-]+$', data['name']):
        print(f"Invalid module name: {data['name']}")
        return False

    if not re.match(r'^[a-zA-Z0-9_.-]+$', data['package']):
        print(f"Invalid package name: {data['package']}")
        return False

    repo = data.get('repository', '')
    if not (repo.startswith('https://github.com/') or repo.startswith('https://codeberg.org/')):
        print(f"Invalid repository URL: {repo}")
        return False

    return True


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

    if not validate_submission(submission):
        print("Validation failed")
        sys.exit(1)

    try:
        with open('packages.json', 'r', encoding='utf-8') as f:
            packages = json.load(f)
    except Exception as e:
        print(f"Cannot read packages.json: {e}")
        sys.exit(1)

    submit_type = submission.get('type', 'module')
    category_map = {
        'module': 'modules',
        'adapter': 'adapters',
        'cli_extension': 'cli_extensions'
    }
    category = category_map.get(submit_type, 'modules')

    if category not in packages:
        print(f"Category '{category}' not found in packages.json")
        sys.exit(1)

    module_name = submission['name']
    if module_name in packages[category]:
        print(f"Module '{module_name}' already exists in {category}")
        sys.exit(1)

    entry = {
        'package': submission['package'],
        'version': submission.get('version', '0.0.0'),
        'author': submission['author'],
        'description': submission['description'],
        'repository': submission['repository'],
        'official': submission.get('official', False),
        'verified': False,
        'submitted_by': submission.get('submitted_by', ''),
        'tags': submission.get('tags', [])
    }

    if submit_type != 'adapter' and submission.get('min_sdk_version'):
        entry['min_sdk_version'] = submission['min_sdk_version']

    packages[category][module_name] = entry

    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    packages['last_updated'] = current_time

    try:
        with open('packages.json', 'w', encoding='utf-8') as f:
            json.dump(packages, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Cannot write packages.json: {e}")
        sys.exit(1)

    print(f"Successfully added '{module_name}' to {category}")
    print(f"verified: false, submitted_by: {submission.get('submitted_by', '')}")

    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"module_name={module_name}\n")


if __name__ == '__main__':
    handle_submission()
