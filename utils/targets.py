"""Validated target lists and task-local target selection."""
from contextvars import ContextVar
from urllib.parse import urlparse
import config.settings as cfg

current_target = ContextVar("current_target", default=None)

def get_target_url():
    return current_target.get() or cfg.TARGET_URL

def parse_targets(text):
    targets = []
    for line, raw in enumerate(text.splitlines(), 1):
        url = raw.strip()
        if not url:
            continue
        try:
            parsed = urlparse(url)
            valid = parsed.scheme in ("http", "https") and parsed.hostname and not any(c.isspace() for c in url)
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(f"URL line {line} is invalid: {url}")
        if url not in targets:
            targets.append(url)
    if not targets:
        raise ValueError("Enter at least one full URL, e.g. https://example.com")
    return targets
