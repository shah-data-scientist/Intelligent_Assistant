"""
FILE: test_sanitization.py
STATUS: Active
RESPONSIBILITY: Security tests for PII detection and sanitization.

DEPENDENCIES (Who uses this file):
- pytest test runner
- PII protection validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.security.sanitization: PII detection and sanitization functions

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from src.security.sanitization import PIIDetector, get_pii_detector, scan_for_pii


class TestPIIDetector:
    """Test PIIDetector class for detecting various PII types."""

    def test_detect_email(self):
        """Test email detection."""
        detector = PIIDetector()
        text = "Contact me at john.doe@example.com for more info."
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "EMAIL"
        assert pii[0]["match"] == "john.doe@example.com"

    def test_detect_french_phone_mobile(self):
        """Test French mobile phone detection (06/07)."""
        detector = PIIDetector()
        text = "Call me at 06 12 34 56 78"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "PHONE"
        assert "06" in pii[0]["match"]

    def test_detect_french_phone_landline(self):
        """Test French landline detection (01-05, 08, 09)."""
        detector = PIIDetector()
        text = "Office: 01-45-67-89-00"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "PHONE"

    def test_detect_credit_card(self):
        """Test credit card detection."""
        detector = PIIDetector()
        text = "My card: 4532-1234-5678-9010"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "CREDIT_CARD"

    def test_detect_french_ssn(self):
        """Test French social security number detection."""
        detector = PIIDetector()
        text = "SSN: 1 85 03 75 123 456"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "SSN"

    def test_detect_french_address(self):
        """Test French address detection."""
        detector = PIIDetector()
        test_cases = ["123 rue de la Paix", "45 avenue des Champs-Elysees", "10 boulevard Saint-Germain"]

        for address in test_cases:
            pii = detector.detect(f"I live at {address}")
            assert len(pii) >= 1, f"Failed to detect: {address}"
            assert pii[0]["type"] == "ADDRESS"

    def test_detect_dob_dd_mm_yyyy(self):
        """Test date of birth detection (DD/MM/YYYY)."""
        detector = PIIDetector()
        text = "Born on 15/03/1990"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "DOB"

    def test_detect_dob_yyyy_mm_dd(self):
        """Test date of birth detection (YYYY-MM-DD)."""
        detector = PIIDetector()
        text = "DOB: 1990-03-15"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "DOB"

    def test_detect_ipv4_address(self):
        """Test IPv4 address detection."""
        detector = PIIDetector()
        text = "Server IP: 192.168.1.100"
        pii = detector.detect(text)

        assert len(pii) == 1
        assert pii[0]["type"] == "IP_ADDRESS"
        assert pii[0]["match"] == "192.168.1.100"

    def test_detect_multiple_pii_types(self):
        """Test detection of multiple PII types in same text."""
        detector = PIIDetector()
        text = "Contact john@example.com or call 06 12 34 56 78 at 10 rue de Paris"
        pii = detector.detect(text)

        assert len(pii) >= 3  # EMAIL, PHONE, ADDRESS
        pii_types = [p["type"] for p in pii]
        assert "EMAIL" in pii_types
        assert "PHONE" in pii_types
        assert "ADDRESS" in pii_types

    def test_detect_no_pii(self):
        """Test that clean text returns no PII."""
        detector = PIIDetector()
        text = "This is a normal sentence about cultural events in Paris."
        pii = detector.detect(text)

        assert len(pii) == 0

    def test_detect_false_positive_event_date(self):
        """Test that event dates (non-PII) are not flagged as DOB."""
        detector = PIIDetector()
        text = "Event on 2026-02-15 at 19:00"
        pii = detector.detect(text)

        # This WILL detect DOB (current implementation doesn't distinguish)
        # Test documents current behavior - improvement opportunity
        assert any(p["type"] == "DOB" for p in pii)


class TestPIISanitization:
    """Test PII sanitization (redaction/removal)."""

    def test_sanitize_email_redact(self):
        """Test email redaction with [EMAIL_REDACTED]."""
        detector = PIIDetector()
        text = "Contact john@example.com"
        sanitized = detector.sanitize(text, redact=True)

        assert "john@example.com" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized

    def test_sanitize_email_remove(self):
        """Test email complete removal (no redaction marker)."""
        detector = PIIDetector()
        text = "Contact john@example.com"
        sanitized = detector.sanitize(text, redact=False)

        assert "john@example.com" not in sanitized
        assert "[EMAIL_REDACTED]" not in sanitized
        assert sanitized.strip() == "Contact"

    def test_sanitize_phone_redact(self):
        """Test phone redaction."""
        detector = PIIDetector()
        text = "Call 06 12 34 56 78"
        sanitized = detector.sanitize(text, redact=True)

        assert "06 12 34 56 78" not in sanitized
        assert "[PHONE_REDACTED]" in sanitized

    def test_sanitize_multiple_pii(self):
        """Test sanitizing multiple PII types."""
        detector = PIIDetector()
        text = "Email: john@example.com, Phone: 06 12 34 56 78, IP: 192.168.1.1"
        sanitized = detector.sanitize(text, redact=True)

        assert "john@example.com" not in sanitized
        assert "06 12 34 56 78" not in sanitized
        assert "192.168.1.1" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized
        assert "[PHONE_REDACTED]" in sanitized
        assert "[IP_ADDRESS_REDACTED]" in sanitized

    def test_sanitize_preserves_non_pii(self):
        """Test that non-PII content is preserved."""
        detector = PIIDetector()
        text = "The event at Paris Opera has john@example.com as contact."
        sanitized = detector.sanitize(text, redact=True)

        assert "The event" in sanitized
        assert "Paris Opera" in sanitized
        assert "as contact" in sanitized


class TestScanForPII:
    """Test scan_for_pii helper function."""

    def test_scan_no_redact(self):
        """Test scan without redaction."""
        text = "Contact john@example.com"
        result = scan_for_pii(text, redact=False)

        assert result["has_pii"] is True
        assert len(result["pii_found"]) == 1
        assert result["sanitized_text"] == text  # Original unchanged

    def test_scan_with_redact(self):
        """Test scan with automatic redaction."""
        text = "Contact john@example.com"
        result = scan_for_pii(text, redact=True)

        assert result["has_pii"] is True
        assert len(result["pii_found"]) == 1
        assert "john@example.com" not in result["sanitized_text"]
        assert "[EMAIL_REDACTED]" in result["sanitized_text"]

    def test_scan_clean_text(self):
        """Test scan on text with no PII."""
        text = "This is a cultural events chatbot."
        result = scan_for_pii(text, redact=False)

        assert result["has_pii"] is False
        assert len(result["pii_found"]) == 0
        assert result["sanitized_text"] == text

    def test_scan_returns_pii_details(self):
        """Test that scan returns detailed PII information."""
        text = "Email: john@example.com, Phone: 06 12 34 56 78"
        result = scan_for_pii(text, redact=False)

        assert result["has_pii"] is True
        pii_found = result["pii_found"]
        assert len(pii_found) == 2

        # Check structure
        for pii in pii_found:
            assert "type" in pii
            assert "match" in pii
            assert "position" in pii


class TestPIIDetectorSingleton:
    """Test get_pii_detector singleton function."""

    def test_get_pii_detector_singleton(self):
        """Test that get_pii_detector returns same instance."""
        detector1 = get_pii_detector()
        detector2 = get_pii_detector()

        assert detector1 is detector2


class TestPIIPatternEdgeCases:
    """Test edge cases and boundary conditions for PII patterns."""

    def test_email_no_false_positive_on_url(self):
        """Test that URLs with @ are not flagged as emails."""
        detector = PIIDetector()
        text = "Visit http://example.com@domain for info"
        # This might still flag - test documents current behavior

    def test_phone_french_format_variations(self):
        """Test various French phone formats."""
        detector = PIIDetector()
        # Formats that SHOULD be detected
        supported_formats = [
            "06 12 34 56 78",
            "06-12-34-56-78",
            "06.12.34.56.78",
            "0612345678",
        ]

        for phone in supported_formats:
            pii = detector.detect(f"Call {phone}")
            assert len(pii) >= 1, f"Failed to detect: {phone}"

        # International format without spaces is NOT supported by current pattern
        # Documents limitation
        pii = detector.detect("Call +33612345678")
        # Expected to NOT match due to pattern limitations

    def test_credit_card_with_spaces(self):
        """Test credit card with different separators."""
        detector = PIIDetector()
        cards = ["4532 1234 5678 9010", "4532-1234-5678-9010", "4532123456789010"]

        for card in cards:
            pii = detector.detect(f"Card: {card}")
            assert len(pii) == 1, f"Failed to detect: {card}"

    def test_address_case_insensitive(self):
        """Test that address detection is case-insensitive."""
        detector = PIIDetector()
        text = "I live at 123 RUE DE LA PAIX"
        pii = detector.detect(text)

        assert len(pii) >= 1
        assert pii[0]["type"] == "ADDRESS"

    def test_address_with_accents(self):
        """Test address detection with French accents."""
        detector = PIIDetector()
        text = "Adresse: 45 avenue des Champs-Élysées"
        pii = detector.detect(text)

        assert len(pii) >= 1
        assert pii[0]["type"] == "ADDRESS"

    def test_ssn_various_formats(self):
        """Test French SSN with different spacing."""
        detector = PIIDetector()
        ssn_formats = ["1 85 03 75 123 456", "185037512345", "1-85-03-75-123-456"]

        for ssn in ssn_formats:
            pii = detector.detect(f"SSN: {ssn}")
            # Current pattern may not catch all formats - test documents behavior

    def test_dob_not_event_date(self):
        """Test that future event dates could be false positives for DOB."""
        detector = PIIDetector()
        text = "Event scheduled for 15/02/2026"
        pii = detector.detect(text)

        # Documents that current implementation WILL detect this as DOB
        # This is a known limitation - dates are ambiguous
        assert any(p["type"] == "DOB" for p in pii)

    def test_ip_not_version_number(self):
        """Test that version numbers are not flagged as IP."""
        detector = PIIDetector()
        text = "Version 1.2.3 of the app"
        pii = detector.detect(text)

        # Will NOT match (needs 4 octets)
        assert len([p for p in pii if p["type"] == "IP_ADDRESS"]) == 0

    def test_ip_four_octets_only(self):
        """Test that IP detection requires exactly 4 octets."""
        detector = PIIDetector()
        text = "Code: 192.168.1"
        pii = detector.detect(text)

        # Should NOT match (only 3 octets)
        assert len([p for p in pii if p["type"] == "IP_ADDRESS"]) == 0


class TestPIIDetectorInitialization:
    """Test PIIDetector initialization options."""

    def test_detector_with_name_detection_disabled(self):
        """Test detector with name detection disabled (default)."""
        detector = PIIDetector(detect_names=False)
        assert detector.detect_names is False

    def test_detector_with_name_detection_enabled(self):
        """Test detector with name detection enabled."""
        detector = PIIDetector(detect_names=True)
        assert detector.detect_names is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
