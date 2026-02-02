"""
FILE: test_sanitization.py
STATUS: Active
RESPONSIBILITY: Unit tests for PII detection and sanitization.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from src.security.sanitization import (
    PIIDetector,
    get_pii_detector,
    scan_for_pii,
)


class TestPIIDetector:
    """Test PIIDetector class."""

    def test_detect_email(self):
        """Test email detection."""
        detector = PIIDetector()
        text = "Contact me at john.doe@example.com for more info"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "EMAIL"
        assert pii[0]["match"] == "john.doe@example.com"

    def test_detect_french_phone(self):
        """Test French phone number detection."""
        detector = PIIDetector()

        # Standard French mobile number
        text = "Appelez-moi au 06 12 34 56 78"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "PHONE"

    def test_detect_french_phone_landline(self):
        """Test French landline detection (01-05 prefixes)."""
        detector = PIIDetector()
        # French landline starting with 01 (Paris region)
        text = "Appelez-nous au 01 23 45 67 89"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "PHONE"

    def test_detect_credit_card(self):
        """Test credit card number detection."""
        detector = PIIDetector()
        text = "My card is 1234-5678-9012-3456"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "CREDIT_CARD"

    def test_detect_french_address(self):
        """Test French address detection."""
        detector = PIIDetector()
        text = "J'habite au 15 rue de la Paix à Paris"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "ADDRESS"

    def test_detect_dob(self):
        """Test date of birth detection."""
        detector = PIIDetector()

        # DD/MM/YYYY format
        text = "Né le 15/03/1990"
        pii = detector.detect(text)
        assert len(pii) == 1
        assert pii[0]["type"] == "DOB"

        # YYYY-MM-DD format
        text2 = "Date: 1990-03-15"
        pii2 = detector.detect(text2)
        assert len(pii2) == 1
        assert pii2[0]["type"] == "DOB"

    def test_detect_ip_address(self):
        """Test IP address detection."""
        detector = PIIDetector()
        text = "Server at 192.168.1.100"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "IP_ADDRESS"

    def test_detect_multiple_pii(self):
        """Test detection of multiple PII types."""
        detector = PIIDetector()
        text = "Email: test@example.com, Phone: 06 12 34 56 78"
        pii = detector.detect(text)

        assert len(pii) == 2
        pii_types = [p["type"] for p in pii]
        assert "EMAIL" in pii_types
        assert "PHONE" in pii_types

    def test_detect_no_pii(self):
        """Test text with no PII."""
        detector = PIIDetector()
        text = "Concerts de jazz à Paris ce weekend"
        pii = detector.detect(text)

        assert len(pii) == 0

    def test_sanitize_with_redact(self):
        """Test sanitization with redaction."""
        detector = PIIDetector()
        text = "Contact: john@example.com"
        sanitized = detector.sanitize(text, redact=True)

        assert "john@example.com" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized

    def test_sanitize_without_redact(self):
        """Test sanitization with removal (no redaction marker)."""
        detector = PIIDetector()
        text = "Contact: john@example.com"
        sanitized = detector.sanitize(text, redact=False)

        assert "john@example.com" not in sanitized
        assert "REDACTED" not in sanitized
        assert "Contact: " in sanitized


class TestGetPIIDetector:
    """Test PII detector singleton."""

    def test_returns_detector(self):
        """Test that function returns a PIIDetector."""
        detector = get_pii_detector()
        assert isinstance(detector, PIIDetector)

    def test_returns_same_instance(self):
        """Test that function returns singleton."""
        detector1 = get_pii_detector()
        detector2 = get_pii_detector()
        assert detector1 is detector2


class TestScanForPII:
    """Test scan_for_pii function."""

    def test_scan_no_pii(self):
        """Test scanning text with no PII."""
        result = scan_for_pii("Concerts de jazz à Paris")

        assert result["has_pii"] is False
        assert result["pii_found"] == []
        assert result["sanitized_text"] == "Concerts de jazz à Paris"

    def test_scan_with_pii_no_redact(self):
        """Test scanning with PII but no redaction."""
        result = scan_for_pii("Email: test@example.com", redact=False)

        assert result["has_pii"] is True
        assert len(result["pii_found"]) == 1
        # Without redact, original text is returned
        assert result["sanitized_text"] == "Email: test@example.com"

    def test_scan_with_pii_and_redact(self):
        """Test scanning with PII and redaction enabled."""
        result = scan_for_pii("Email: test@example.com", redact=True)

        assert result["has_pii"] is True
        assert len(result["pii_found"]) == 1
        # With redact, PII should be replaced
        assert "test@example.com" not in result["sanitized_text"]
        assert "[EMAIL_REDACTED]" in result["sanitized_text"]

    def test_scan_multiple_pii_redact(self):
        """Test scanning multiple PII with redaction."""
        text = "Contact: john@example.com, Tel: 06 12 34 56 78"
        result = scan_for_pii(text, redact=True)

        assert result["has_pii"] is True
        assert len(result["pii_found"]) == 2
        assert "john@example.com" not in result["sanitized_text"]
        assert "06 12 34 56 78" not in result["sanitized_text"]


class TestPIIPatterns:
    """Test PII pattern completeness."""

    def test_email_pattern_variations(self):
        """Test various email format variations."""
        detector = PIIDetector()

        emails = [
            "simple@example.com",
            "name.surname@domain.co.uk",
            "name+tag@example.org",
            "user123@test-domain.fr",
        ]

        for email in emails:
            pii = detector.detect(f"Contact: {email}")
            assert len(pii) == 1, f"Failed to detect: {email}"
            assert pii[0]["match"] == email

    def test_phone_pattern_variations(self):
        """Test various French phone number formats."""
        detector = PIIDetector()

        # Standard French formats starting with 0
        phones = [
            "0612345678",
            "06 12 34 56 78",
            "06.12.34.56.78",
            "06-12-34-56-78",
        ]

        for phone in phones:
            pii = detector.detect(f"Tel: {phone}")
            assert len(pii) >= 1, f"Failed to detect: {phone}"

    def test_phone_landline_formats(self):
        """Test French landline number formats (01-05 prefixes)."""
        detector = PIIDetector()
        landlines = [
            "01 23 45 67 89",  # Paris
            "02.34.56.78.90",  # Northwest
            "03-45-67-89-01",  # Northeast
        ]
        for phone in landlines:
            pii = detector.detect(f"Tel: {phone}")
            assert len(pii) >= 1, f"Failed to detect: {phone}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
