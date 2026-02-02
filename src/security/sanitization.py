"""
FILE: sanitization.py
STATUS: Active
RESPONSIBILITY: Output sanitization to detect and remove PII from LLM responses.

DEPENDENCIES (Who uses this file):
- src/api/endpoints.py: Sanitizes responses before returning to client

IMPORTS (What this file needs):
- logging: For logging PII detections
- re: For regex-based pattern matching

LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: Security Team
"""

import logging
import re

logger = logging.getLogger(__name__)


class PIIDetector:
    """Detect personally identifiable information in text with enhanced patterns."""

    # Regex patterns for common PII
    EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    PHONE_PATTERN = r"\b(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}\b"  # French phone numbers
    CREDIT_CARD_PATTERN = r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
    SSN_PATTERN = r"\b\d{1}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\b"  # French SSN (Numéro de sécurité sociale)

    # ADDRESS_PATTERN DISABLED - venue addresses are public information, not PII
    # Users need venue addresses to attend events (core functionality)
    # ADDRESS_PATTERN = r"\b\d{1,5}\s+(rue|avenue|boulevard|place|allée|impasse|chemin|voie|cours|quai|square|passage)\s+[A-Za-zÀ-ÿ\s\'-]{3,50}"
    # DOB_PATTERN DISABLED - causes false positives with event dates (core functionality)
    # DOB_PATTERN = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
    IP_PATTERN = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"  # IPv4 addresses
    # Name pattern (DISABLED by default to avoid false positives with event organizers)

    def __init__(self, detect_names: bool = False):
        """Initialize PII detector.

        Args:
            detect_names: If True, enable name pattern detection (may have false positives)
        """
        self.patterns = {
            "EMAIL": re.compile(self.EMAIL_PATTERN),
            "PHONE": re.compile(self.PHONE_PATTERN),
            "CREDIT_CARD": re.compile(self.CREDIT_CARD_PATTERN),
            "SSN": re.compile(self.SSN_PATTERN),
            # ADDRESS pattern removed - venue addresses are public info, not PII
            # DOB pattern removed - event dates are core functionality, not PII
            "IP_ADDRESS": re.compile(self.IP_PATTERN),
        }

        # Optional: Enable name detection (higher false positive rate)
        self.detect_names = detect_names

    def detect(self, text: str) -> list[dict]:
        """Detect PII in text.

        Args:
            text: Text to scan

        Returns:
            List of dictionaries with keys:
                - type (str): PII type (EMAIL, PHONE, etc.)
                - match (str): The matched text
                - position (int): Start position in text
        """
        found_pii = []

        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                pii_entry = {"type": pii_type, "match": match.group(), "position": match.start()}
                found_pii.append(pii_entry)
                logger.warning(f"Detected {pii_type} in output: {match.group()}")

        return found_pii

    def sanitize(self, text: str, redact: bool = True) -> str:
        """Remove or redact PII from text.

        Args:
            text: Text to sanitize
            redact: If True, replace with [REDACTED], else remove entirely

        Returns:
            Sanitized text
        """
        sanitized = text

        # Redact or remove each PII type
        for pii_type, pattern in self.patterns.items():
            if redact:
                replacement = f"[{pii_type.upper()}_REDACTED]"
            else:
                replacement = ""

            sanitized = pattern.sub(replacement, sanitized)

        return sanitized


# Global singleton
_global_detector = None


def get_pii_detector() -> PIIDetector:
    """Get global PII detector instance.

    Returns:
        PIIDetector singleton
    """
    global _global_detector
    if _global_detector is None:
        _global_detector = PIIDetector()
    return _global_detector


def scan_for_pii(text: str, redact: bool = False) -> dict:
    """Scan text for PII and optionally sanitize.

    Args:
        text: Text to scan
        redact: If True, automatically redact PII

    Returns:
        Dictionary with keys:
            - sanitized_text (str): Original or redacted text
            - pii_found (list): List of PII dictionaries
            - has_pii (bool): Whether PII was detected
    """
    detector = get_pii_detector()
    pii_found = detector.detect(text)
    has_pii = len(pii_found) > 0

    if has_pii:
        pii_types = [pii["type"] for pii in pii_found]
        logger.warning(f"PII detected in output: {pii_types}")

        if redact:
            sanitized = detector.sanitize(text, redact=True)
            return {"sanitized_text": sanitized, "pii_found": pii_found, "has_pii": True}

    return {"sanitized_text": text, "pii_found": pii_found, "has_pii": has_pii}
