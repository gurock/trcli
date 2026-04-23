"""
Unit tests for QualityRatingParser - AI Evaluation Template support

Tests cover:
- Valid quality rating parsing
- Validation rules (max categories, star range, non-zero requirement)
- Edge cases and error handling
- JSON format validation
"""

import pytest
from trcli.data_classes.data_parsers import QualityRatingParser


class TestQualityRatingParser:
    """Test suite for QualityRatingParser validation and parsing"""

    # ========== Valid Quality Ratings ==========

    @pytest.mark.parametrize(
        "rating_str,expected_categories",
        [
            # Single category
            ('{"accuracy": 5}', 1),
            # Multiple categories
            ('{"accuracy": 5, "speed": 4}', 2),
            ('{"accuracy": 5, "speed": 4, "reliability": 3}', 3),
            # Maximum 15 categories
            (
                '{"cat1": 5, "cat2": 4, "cat3": 3, "cat4": 2, "cat5": 1, '
                '"cat6": 5, "cat7": 4, "cat8": 3, "cat9": 2, "cat10": 1, '
                '"cat11": 5, "cat12": 4, "cat13": 3, "cat14": 2, "cat15": 1}',
                15,
            ),
            # All valid star values (0-5)
            ('{"val0": 0, "val1": 1, "val2": 2, "val3": 3, "val4": 4, "val5": 5}', 6),
            # Real-world AI evaluation categories
            ('{"factual_accuracy": 5, "relevance": 5, "completeness": 4, ' '"clarity": 3, "tone": 4}', 5),
        ],
        ids=[
            "single_category",
            "two_categories",
            "three_categories",
            "max_15_categories",
            "all_star_values_0_to_5",
            "realistic_ai_categories",
        ],
    )
    def test_parse_valid_quality_ratings(self, rating_str, expected_categories):
        """Test parsing of valid quality ratings"""
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None, f"Expected no error, got: {error}"
        assert result is not None, "Expected parsed result, got None"
        assert len(result) == expected_categories
        assert isinstance(result, dict)

        # Verify all values are in valid range
        for category, value in result.items():
            assert isinstance(value, int)
            assert 0 <= value <= 5

    def test_parse_quality_rating_with_zero_values(self):
        """Test that zero values are allowed if at least one category >= 1"""
        rating_str = '{"accuracy": 5, "speed": 0, "reliability": 0}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert result == {"accuracy": 5, "speed": 0, "reliability": 0}

    # ========== Invalid Quality Ratings - Max Categories ==========

    def test_parse_quality_rating_exceeds_max_categories(self):
        """Test that more than 15 categories is rejected"""
        # 16 categories
        rating_str = (
            '{"cat1": 5, "cat2": 4, "cat3": 3, "cat4": 2, "cat5": 1, '
            '"cat6": 5, "cat7": 4, "cat8": 3, "cat9": 2, "cat10": 1, '
            '"cat11": 5, "cat12": 4, "cat13": 3, "cat14": 2, "cat15": 1, '
            '"cat16": 5}'
        )
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "at most 15 categories" in error
        assert "found 16" in error

    # ========== Invalid Quality Ratings - Star Value Range ==========

    @pytest.mark.parametrize(
        "rating_str,expected_error_fragment",
        [
            ('{"accuracy": 6}', "between 0 and 5"),
            ('{"accuracy": 10}', "between 0 and 5"),
            ('{"accuracy": -1}', "between 0 and 5"),
            ('{"accuracy": 100}', "between 0 and 5"),
        ],
        ids=["value_6", "value_10", "negative_value", "value_100"],
    )
    def test_parse_quality_rating_out_of_range(self, rating_str, expected_error_fragment):
        """Test that star values outside 0-5 range are rejected"""
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert expected_error_fragment in error

    def test_parse_quality_rating_float_value(self):
        """Test that float values are rejected (must be integers)"""
        rating_str = '{"accuracy": 4.5}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "must be integers" in error.lower() or "int" in error.lower()

    # ========== Invalid Quality Ratings - All Zeros ==========

    def test_parse_quality_rating_all_zeros(self):
        """Test that all zero values are rejected"""
        rating_str = '{"accuracy": 0, "speed": 0, "reliability": 0}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "at least one category" in error
        assert ">= 1" in error or "greater than" in error.lower()

    # ========== Invalid Quality Ratings - JSON Format ==========

    @pytest.mark.parametrize(
        "rating_str,expected_error_fragment",
        [
            ("", "cannot be empty"),
            ("   ", "cannot be empty"),
            ("not valid json", "valid JSON"),
            ('{"accuracy": }', "valid JSON"),
            ('{"accuracy": 5,}', "valid JSON"),  # Trailing comma
            ("{accuracy: 5}", "valid JSON"),  # Missing quotes on key
            ("{'accuracy': 5}", "valid JSON"),  # Single quotes instead of double
        ],
        ids=[
            "empty_string",
            "whitespace_only",
            "not_json",
            "incomplete_json",
            "trailing_comma",
            "unquoted_key",
            "single_quotes",
        ],
    )
    def test_parse_quality_rating_invalid_json(self, rating_str, expected_error_fragment):
        """Test that invalid JSON is rejected with appropriate error"""
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert expected_error_fragment.lower() in error.lower()

    def test_parse_quality_rating_json_array(self):
        """Test that JSON array is rejected (must be object)"""
        rating_str = '[{"accuracy": 5}]'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "must be a JSON object" in error or "object" in error.lower()

    def test_parse_quality_rating_json_string(self):
        """Test that JSON string is rejected (must be object)"""
        rating_str = '"accuracy: 5"'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "must be a JSON object" in error or "str" in error.lower()

    def test_parse_quality_rating_json_number(self):
        """Test that JSON number is rejected (must be object)"""
        rating_str = "42"
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None

    def test_parse_quality_rating_empty_object(self):
        """Test that empty JSON object is rejected"""
        rating_str = "{}"
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "cannot be an empty object" in error

    # ========== Invalid Quality Ratings - Category Names ==========

    def test_parse_quality_rating_empty_category_name(self):
        """Test that empty category names are rejected"""
        rating_str = '{"": 5}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "non-empty strings" in error

    def test_parse_quality_rating_whitespace_category_name(self):
        """Test that whitespace-only category names are rejected"""
        rating_str = '{"   ": 5}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert result is None
        assert error is not None
        assert "non-empty strings" in error

    # ========== Edge Cases ==========

    def test_parse_quality_rating_unicode_categories(self):
        """Test that unicode category names are supported"""
        rating_str = '{"précision": 5, "velocità": 4, "信頼性": 3}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert result is not None
        assert len(result) == 3
        assert result["précision"] == 5

    def test_parse_quality_rating_special_chars_in_names(self):
        """Test category names with special characters"""
        rating_str = '{"fact_accuracy": 5, "response-time": 4, "reliability.score": 3}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert result is not None
        assert len(result) == 3

    def test_parse_quality_rating_long_category_names(self):
        """Test that long category names are accepted"""
        long_name = "a" * 200
        rating_str = f'{{"{long_name}": 5}}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert result is not None
        assert result[long_name] == 5

    # ========== Real-World Examples ==========

    def test_parse_quality_rating_ai_chatbot_example(self):
        """Test realistic AI chatbot quality rating"""
        rating_str = (
            '{"factual_accuracy": 5, "relevance": 5, "completeness": 4, '
            '"clarity": 4, "tone": 5, "context_awareness": 4}'
        )
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert len(result) == 6
        assert all(0 <= v <= 5 for v in result.values())

    def test_parse_quality_rating_facial_recognition_example(self):
        """Test realistic facial recognition quality rating"""
        rating_str = '{"factual_accuracy": 5, "recognition_speed": 5, ' '"reliability": 5, "user_experience": 4}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert len(result) == 4
        assert result["factual_accuracy"] == 5
        assert result["user_experience"] == 4

    def test_parse_quality_rating_performance_testing_example(self):
        """Test realistic performance testing quality rating"""
        rating_str = '{"responsiveness": 3, "degradation": 4, "stability": 5, ' '"resource_usage": 3}'
        result, error = QualityRatingParser.parse_quality_rating(rating_str)

        assert error is None
        assert len(result) == 4
        assert all(0 <= v <= 5 for v in result.values())

    # ========== Parser Constants ==========

    def test_quality_rating_parser_constants(self):
        """Test that parser constants are correctly defined"""
        assert QualityRatingParser.MAX_CATEGORIES == 15
        assert QualityRatingParser.MIN_STAR_VALUE == 0
        assert QualityRatingParser.MAX_STAR_VALUE == 5
