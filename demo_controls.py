"""Small, single-process limits for a shared, disk-backed demo."""
import datetime
import json
import os
import tempfile
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore, RLock
from fastapi import HTTPException

_lock = RLock()
_recent = {'ai': deque(), 'create': deque()}
_slots = BoundedSemaphore(2)

def demo_enabled():
    return os.environ.get('DEMO_MODE', 'true').lower() not in ('0', 'false', 'no')

def positive_env(name, default):
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default

def limits():
    return {'ai_per_day': positive_env('DEMO_AI_DAILY_LIMIT', 40),
            'ai_per_minute': positive_env('DEMO_AI_MINUTE_LIMIT', 5),
            'creates_per_day': positive_env('DEMO_CREATE_DAILY_LIMIT', 20),
            'active_cases': positive_env('DEMO_ACTIVE_CASE_LIMIT', 40),
            'stored_cases': positive_env('DEMO_STORED_CASE_LIMIT', 100)}

def consume(action, cases_file):
    if not demo_enabled():
        return
    now = time.time()
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    path = Path(cases_file).with_name(Path(cases_file).name + '.demo-usage.json')
    cap = limits()['ai_per_day' if action == 'ai' else 'creates_per_day']
    with _lock:
        recent = _recent[action]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        minute_cap = limits()['ai_per_minute'] if action == 'ai' else 5
        if len(recent) >= minute_cap:
            raise HTTPException(429, 'Shared demo is busy. Please wait one minute and try again.', headers={'Retry-After': '60'})
        temporary = None
        try:
            usage = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            if not isinstance(usage, dict):
                raise ValueError('Invalid usage ledger')
            if usage.get('day') != today:
                usage = {'day': today, 'ai': 0, 'create': 0}
            if type(usage.get(action, 0)) is not int or usage.get(action, 0) < 0:
                raise ValueError('Invalid counter')
            if usage.get(action, 0) >= cap:
                raise HTTPException(429, 'The shared demo has reached its daily ' + ('AI request' if action == 'ai' else 'case creation') + ' limit. Please return after midnight UTC.')
            usage[action] = usage.get(action, 0) + 1
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
                temporary = file.name
                json.dump(usage, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        except (OSError, ValueError):
            raise HTTPException(503, 'Demo usage limits could not be checked. Please try later.')
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        recent.append(now)

@contextmanager
def ai_request(cases_file):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'Two AI requests are already running. Please try again shortly.', headers={'Retry-After': '10'})
    try:
        consume('ai', cases_file)
        yield
    finally:
        _slots.release()
