"""Tests for ESIA extractor module"""
import pytest
from esia_extractor import (
    slugify,
    normalize_unit,
    chunk_markdown,
    UNIT_CONVERSIONS,
)


class TestSlugify:
    """Test suite for slugify function"""

    @pytest.mark.unit
    def test_slugify_simple(self):
        """Test basic slugification"""
        assert slugify("Project Area") == "project_area"

    @pytest.mark.unit
    def test_slugify_with_parentheses(self):
        """Test slugification with special characters"""
        assert slugify("Coal production (annual)") == "coal_production_annual"

    @pytest.mark.unit
    def test_slugify_with_numbers(self):
        """Test slugification preserves numbers"""
        assert slugify("CO2 emissions") == "co2_emissions"

    @pytest.mark.unit
    def test_slugify_unicode(self):
        """Test slugification handles unicode"""
        result = slugify("Área del proyecto")
        assert result == "area_del_proyecto"


class TestUnitNormalization:
    """Test suite for unit normalization"""

    @pytest.mark.unit
    def test_normalize_mass_units(self):
        """Test mass unit normalization"""
        value, unit = normalize_unit(1, "tonne")
        assert value == 1000.0
        assert unit == "kg"

    @pytest.mark.unit
    def test_normalize_area_units(self):
        """Test area unit normalization"""
        value, unit = normalize_unit(1, "km²")
        assert value == 100.0
        assert unit == "ha"

    @pytest.mark.unit
    def test_normalize_power_units(self):
        """Test power unit normalization"""
        value, unit = normalize_unit(1000, "kW")
        assert value == 1.0
        assert unit == "MW"

    @pytest.mark.unit
    def test_normalize_unknown_unit(self):
        """Test unknown unit returns as-is"""
        value, unit = normalize_unit(42, "unknown_unit")
        assert value == 42
        assert unit == "unknown_unit"

    @pytest.mark.unit
    def test_unit_conversions_defined(self):
        """Test that unit conversions are properly defined"""
        assert len(UNIT_CONVERSIONS) > 0
        assert "kg" in UNIT_CONVERSIONS
        assert "MW" in UNIT_CONVERSIONS


class TestChunking:
    """Test suite for text chunking"""

    @pytest.mark.unit
    def test_chunk_small_text(self):
        """Test chunking of small text returns single chunk"""
        text = "Short text"
        chunks = chunk_markdown(text, max_chars=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    @pytest.mark.unit
    def test_chunk_large_text(self):
        """Test chunking of large text creates multiple chunks"""
        paragraphs = ["Paragraph " + str(i) for i in range(100)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_markdown(text, max_chars=100)
        assert len(chunks) > 1

    @pytest.mark.unit
    def test_chunk_preserves_content(self):
        """Test that chunking preserves all content"""
        text = "Para 1\n\nPara 2\n\nPara 3"
        chunks = chunk_markdown(text, max_chars=50)
        reconstructed = "\n\n".join(chunks)
        assert "Para 1" in reconstructed
        assert "Para 2" in reconstructed
        assert "Para 3" in reconstructed
