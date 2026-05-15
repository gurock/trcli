"""Quality Rating Parser for AI Evaluation Template support"""

import json
from beartype.typing import Tuple, Optional, Dict


class QualityRatingParser:
    """Parser for AI Evaluation Template quality ratings"""

    MAX_CATEGORIES = 15
    MIN_STAR_VALUE = 0
    MAX_STAR_VALUE = 5

    @staticmethod
    def parse_quality_rating(quality_rating_str: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Parse and validate quality rating JSON string.

        Validation rules:
        - Must be valid JSON object
        - Maximum 15 categories
        - Star values must be integers 0-5
        - At least one category must have a value >= 1

        :param quality_rating_str: JSON string containing quality ratings
        :return: Tuple of (quality_rating_dict, error_message)
                 Returns (None, error_message) if validation fails
                 Returns (quality_rating_dict, None) if validation succeeds

        Example valid input:
            '{"factual_accuracy": 5, "relevance": 4, "completeness": 3}'

        Example returns:
            Success: ({"factual_accuracy": 5, "relevance": 4}, None)
            Error: (None, "Quality rating must contain at most 15 categories (found 20)")
        """
        if not quality_rating_str or not quality_rating_str.strip():
            return None, "Quality rating cannot be empty"

        # Parse JSON
        try:
            quality_rating = json.loads(quality_rating_str)
        except json.JSONDecodeError as e:
            return None, f"Quality rating must be valid JSON: {str(e)}"

        # Must be a dictionary
        if not isinstance(quality_rating, dict):
            return None, f"Quality rating must be a JSON object, got {type(quality_rating).__name__}"

        # Check if empty
        if not quality_rating:
            return None, "Quality rating cannot be an empty object"

        # Check max categories
        num_categories = len(quality_rating)
        if num_categories > QualityRatingParser.MAX_CATEGORIES:
            return None, (
                f"Quality rating must contain at most {QualityRatingParser.MAX_CATEGORIES} "
                f"categories (found {num_categories})"
            )

        # Validate star values
        has_non_zero = False
        for category, value in quality_rating.items():
            # Category name validation
            if not isinstance(category, str) or not category.strip():
                return None, f"Category names must be non-empty strings"

            # Value must be an integer
            if not isinstance(value, int):
                return None, (
                    f"Star values must be integers 0-{QualityRatingParser.MAX_STAR_VALUE}, "
                    f"got {type(value).__name__} for category '{category}'"
                )

            # Value must be in valid range
            if value < QualityRatingParser.MIN_STAR_VALUE or value > QualityRatingParser.MAX_STAR_VALUE:
                return None, (
                    f"Star values must be between {QualityRatingParser.MIN_STAR_VALUE} and "
                    f"{QualityRatingParser.MAX_STAR_VALUE}, got {value} for category '{category}'"
                )

            # Track if at least one category has a non-zero value
            if value >= 1:
                has_non_zero = True

        # At least one category must have value >= 1
        if not has_non_zero:
            return None, "Quality rating must have at least one category with a star value >= 1"

        return quality_rating, None
