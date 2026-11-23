"""Require an explicitly selected workspace before live operations."""
import json
import os
import subprocess


def require_workspace():
    expected = os.environ.get('ERM_WORKSPACE_ID')
    if not expected:
        raise RuntimeError('Set ERM_WORKSPACE_ID to your intended workspace ID')
    auth = json.loads(subprocess.run(
        ['deepline', 'auth', 'status', '--json'],
        text=True, capture_output=True, check=True,
    ).stdout)
    if auth['workspace']['id'] != expected:
        raise RuntimeError('Authenticated workspace does not match ERM_WORKSPACE_ID')
