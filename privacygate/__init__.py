"""PrivacyGate: regex-only baseline for conservative PII span masking."""
from .detect import detect, mask

__all__ = ["detect", "mask"]
