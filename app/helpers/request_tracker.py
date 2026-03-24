import os
import resource
import time


def _get_current_rss_mb():
    """Read current RSS from /proc/self/status (Linux). Falls back to maxrss."""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024  # kB -> MB
    except (FileNotFoundError, ValueError, IndexError):
        pass
    # Fallback for macOS / non-Linux
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if os.uname().sysname == "Darwin":
        return maxrss / (1024 * 1024)  # bytes -> MB
    return maxrss / 1024  # kB -> MB


class RequestTracker:
    custom_active = 0
    code_active = 0

    @classmethod
    def total(cls):
        return cls.custom_active + cls.code_active

    @classmethod
    def summary(cls):
        return f"custom={cls.custom_active} code={cls.code_active} total={cls.total()}"

    @classmethod
    def log(cls, tag: str, label: str, extra: str = ""):
        rss = _get_current_rss_mb()
        maxrss_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if os.uname().sysname == "Darwin":
            maxrss = maxrss_raw / (1024 * 1024)
        else:
            maxrss = maxrss_raw / 1024
        parts = [f"[{tag}] {label}", cls.summary(), f"rss={rss:.0f}MB maxrss={maxrss:.0f}MB"]
        if extra:
            parts.append(extra)
        print(" | ".join(parts), flush=True)
