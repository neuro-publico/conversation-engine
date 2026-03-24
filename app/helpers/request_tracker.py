import logging
import resource
import time

logger = logging.getLogger(__name__)


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
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        parts = [f"[{tag}] {label}", cls.summary(), f"maxrss={mem:.0f}MB"]
        if extra:
            parts.append(extra)
        logger.info(" | ".join(parts))
