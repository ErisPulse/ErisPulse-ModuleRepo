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
    category_map = {
        'module': 'modules',
        'adapter': 'adapters'
    }
    category = category_map.get(submit_type, 'modules')

    if category not in packages:
        print(f"Category '{category}' not found in packages.json")
        sys.exit(1)

    module_name = submission['name']

    for cat in ['modules', 'adapters']:
        if module_name in packages.get(cat, {}):
            print(f"Module '{module_name}' already exists in {cat}")
            with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
                f.write(f"error_message=Module '{module_name}' already exists\n")
            sys.exit(1)

    submitted_by = submission.get('submitted_by', '')
    submitted_by_uid = submission.get('submitted_by_uid', '')
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    user_daily_count = 0
    for cat in ['modules', 'adapters']:
        for name, info in packages.get(cat, {}).items():
            if submitted_by_uid and info.get('submitted_by_uid', '') == submitted_by_uid:
                user_daily_count += 1
            elif not submitted_by_uid and info.get('submitted_by', '') == submitted_by:
                user_daily_count += 1

    if user_daily_count >= 3:
        error_msg = f"User '{submitted_by}' has already submitted {user_daily_count} modules. Daily limit is 3."
        print(error_msg)
        with open(os.environ.get('GITHUB_OUTPUT', 'a'), 'a') as f:
            f.write(f"error_message={error_msg}\n")
        sys.exit(1)

    pypi_version = '0.0.0'
    if requests:
        try:
            resp = requests.get(f'https://pypi.org/pypi/{submission["package"]}/json', timeout=15)
            if resp.status_code == 200:
                pypi_version = resp.json()['info'].get('version', '0.0.0')
        except Exception:
            pass

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
        'oauth_provider': submission.get('oauth_provider', ''),
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

    print(f"Successfully added '{module_name}' to {category} (version {pypi_version})")
    print(f"verified: false, submitted_by: {submitted_by}")

    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"module_name={module_name}\n")


if __name__ == '__main__':
    handle_submission()
