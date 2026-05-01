"""Unit tests for quality_rating support via --result-fields"""

import pytest
from trcli.data_classes.dataclass_testrail import TestRailResult
from trcli.data_classes.validation_exception import ValidationException


class TestResultFieldsQualityRating:
    """Test quality_rating handling in --result-fields (CLI global result fields)"""

    def test_quality_rating_via_result_fields_valid(self):
        """Test that valid quality_rating JSON string via --result-fields is parsed and set"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": '{"factual_accuracy": 5, "relevance": 4}', "custom_field": "value1"}

        result.add_global_result_fields(global_fields)

        # quality_rating should be parsed and set on the attribute
        assert result.quality_rating == {"factual_accuracy": 5, "relevance": 4}
        # Other fields should be in result_fields dict
        assert result.result_fields["custom_field"] == "value1"
        # quality_rating should NOT be in result_fields dict
        assert "quality_rating" not in result.result_fields

    def test_quality_rating_via_result_fields_invalid_json(self):
        """Test that invalid JSON in quality_rating raises ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": "{not valid json}"}

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "must be valid JSON" in str(exc_info.value)

    def test_quality_rating_via_result_fields_too_many_categories(self):
        """Test that quality_rating with >15 categories raises ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        # Create 16 categories (exceeds MAX_CATEGORIES=15)
        categories = {f"category_{i}": 3 for i in range(16)}
        global_fields = {"quality_rating": str(categories).replace("'", '"')}

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "at most 15 categories" in str(exc_info.value)

    def test_quality_rating_via_result_fields_invalid_star_value(self):
        """Test that quality_rating with invalid star values raises ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": '{"factual_accuracy": 6}'}  # 6 exceeds MAX_STAR_VALUE=5

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "must be between 0 and 5" in str(exc_info.value)

    def test_quality_rating_via_result_fields_all_zeros(self):
        """Test that quality_rating with all zero values raises ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": '{"factual_accuracy": 0, "relevance": 0}'}

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "at least one category with a star value >= 1" in str(exc_info.value)

    def test_quality_rating_test_specific_overrides_global(self):
        """Test that test-specific quality_rating (from properties) takes precedence over --result-fields"""
        # Simulate test-specific quality_rating already set (from XML properties)
        result = TestRailResult(case_id=1, status_id=1, quality_rating={"test_specific": 5, "accuracy": 4})

        # Attempt to apply global quality_rating via --result-fields
        global_fields = {"quality_rating": '{"global_rating": 3}'}

        result.add_global_result_fields(global_fields)

        # Test-specific rating should be preserved (not overridden by global)
        assert result.quality_rating == {"test_specific": 5, "accuracy": 4}
        assert result.quality_rating != {"global_rating": 3}

    def test_quality_rating_via_result_fields_empty_string(self):
        """Test that empty string quality_rating raises ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": ""}

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "cannot be empty" in str(exc_info.value)

    def test_quality_rating_via_result_fields_empty_object(self):
        """Test that empty JSON object quality_rating raises ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": "{}"}

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "cannot be an empty object" in str(exc_info.value)

    def test_quality_rating_via_result_fields_non_integer_value(self):
        """Test that non-integer star values raise ValidationException"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": '{"factual_accuracy": 4.5}'}  # float instead of int

        with pytest.raises(ValidationException) as exc_info:
            result.add_global_result_fields(global_fields)

        assert "Unable to parse quality_rating in --result-fields" in str(exc_info.value)
        assert "must be integers" in str(exc_info.value)

    def test_quality_rating_via_result_fields_mixed_with_other_fields(self):
        """Test that quality_rating works alongside other result fields"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {
            "quality_rating": '{"factual_accuracy": 5, "relevance": 4, "completeness": 3}',
            "custom_field_1": "value1",
            "custom_field_2": "value2",
            "custom_priority": "3",
        }

        result.add_global_result_fields(global_fields)

        # quality_rating should be on the attribute
        assert result.quality_rating == {"factual_accuracy": 5, "relevance": 4, "completeness": 3}
        # Other fields should be in result_fields dict
        assert result.result_fields["custom_field_1"] == "value1"
        assert result.result_fields["custom_field_2"] == "value2"
        assert result.result_fields["custom_priority"] == "3"
        # quality_rating should NOT be in result_fields dict
        assert "quality_rating" not in result.result_fields

    def test_quality_rating_to_dict_serialization(self):
        """Test that quality_rating is properly serialized in to_dict()"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"quality_rating": '{"factual_accuracy": 5, "security": 4}', "custom_field": "value1"}

        result.add_global_result_fields(global_fields)
        result_dict = result.to_dict()

        # quality_rating should be at root level (not nested)
        assert "quality_rating" in result_dict
        assert result_dict["quality_rating"] == {"factual_accuracy": 5, "security": 4}
        # Other fields should also be present
        assert result_dict["custom_field"] == "value1"
        assert result_dict["case_id"] == 1
        assert result_dict["status_id"] == 1

    def test_no_quality_rating_in_result_fields_no_error(self):
        """Test that absence of quality_rating doesn't cause issues"""
        result = TestRailResult(case_id=1, status_id=1)
        global_fields = {"custom_field_1": "value1", "custom_field_2": "value2"}

        result.add_global_result_fields(global_fields)

        # No quality_rating should be set
        assert result.quality_rating is None
        # Other fields should be in result_fields dict
        assert result.result_fields["custom_field_1"] == "value1"
        assert result.result_fields["custom_field_2"] == "value2"
