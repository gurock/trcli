"""
Unit tests for JUnit XML parser quality rating integration

Tests cover:
- Parsing valid quality ratings from JUnit XML
- Handling invalid quality ratings gracefully
- Backward compatibility (tests without quality ratings)
- Serialization of quality ratings in TestRailResult
- Integration with AI context fields
"""

import pytest
from pathlib import Path
from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.readers.junit_xml import JunitParser


class TestJunitQualityRating:
    """Test suite for JUnit XML quality rating parsing"""

    @pytest.fixture
    def env(self):
        """Create a test environment"""
        env = Environment()
        env.case_matcher = MatchersParser.PROPERTY
        env.special_parser = None
        env.suite_name = "Test Suite"
        env.params_from_config = {}
        return env

    # ========== Valid Quality Ratings ==========

    def test_parse_junit_with_valid_quality_ratings(self, env):
        """Test parsing JUnit XML with valid quality ratings"""
        env.file = Path(__file__).parent / "test_data/XML/quality_rating_valid.xml"
        parser = JunitParser(env)
        suites = parser.parse_file()

        assert len(suites) == 1
        suite = suites[0]
        assert len(suite.testsections) == 1
        section = suite.testsections[0]
        assert len(section.testcases) == 3

        # Test 1: Has quality rating
        test1 = section.testcases[0]
        assert test1.result.case_id == 100
        assert test1.result.quality_rating is not None
        assert test1.result.quality_rating == {"factual_accuracy": 5, "relevance": 5, "completeness": 4}

        # Test 2: No quality rating (backward compatibility)
        test2 = section.testcases[1]
        assert test2.result.case_id == 101
        assert test2.result.quality_rating is None

        # Test 3: Failed test with quality rating
        test3 = section.testcases[2]
        assert test3.result.case_id == 102
        assert test3.result.status_id == 5  # Failed
        assert test3.result.quality_rating is not None
        assert test3.result.quality_rating == {"factual_accuracy": 2, "relevance": 1, "completeness": 2}

    def test_quality_rating_serialization(self, env):
        """Test that quality rating is serialized at root level"""
        env.file = Path(__file__).parent / "test_data/XML/quality_rating_valid.xml"
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result_dict = test_case.result.to_dict()

        # Quality rating should be at root level
        assert "quality_rating" in result_dict
        assert result_dict["quality_rating"] == {"factual_accuracy": 5, "relevance": 5, "completeness": 4}

        # Should not be in result_fields
        assert "quality_rating" not in result_dict.get("result_fields", {})

    def test_quality_rating_with_ai_context_fields(self, env):
        """Test that quality rating works alongside AI context fields"""
        env.file = Path(__file__).parent / "test_data/XML/quality_rating_valid.xml"
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result_dict = test_case.result.to_dict()

        # Quality rating at root level
        assert "quality_rating" in result_dict

        # AI context fields in result_fields
        assert "custom_ai_input" in result_dict
        assert "custom_ai_output" in result_dict
        assert "custom_ai_traces" in result_dict
        assert "custom_ai_latency" in result_dict

        assert result_dict["custom_ai_input"] == "What is the capital of France?"
        assert result_dict["custom_ai_output"] == "The capital of France is Paris."

    # ========== Invalid Quality Ratings ==========

    def test_parse_junit_with_invalid_quality_ratings(self, env, capsys):
        """Test that invalid quality ratings are logged and skipped gracefully"""
        env.file = Path(__file__).parent / "test_data/XML/quality_rating_invalid.xml"
        parser = JunitParser(env)
        suites = parser.parse_file()

        assert len(suites) == 1
        suite = suites[0]
        section = suite.testsections[0]
        assert len(section.testcases) == 3

        # All tests should parse successfully despite invalid quality ratings
        for test_case in section.testcases:
            # Invalid quality ratings should be None
            assert test_case.result.quality_rating is None
            # But test should still have case_id and status
            assert test_case.result.case_id is not None
            assert test_case.result.status_id is not None

        # Check that errors were logged to stderr
        captured = capsys.readouterr()
        stderr_output = captured.err.lower()

        # Verify expected error messages are present
        assert (
            "at most 15" in stderr_output or "too many categories" in stderr_output
        ), "Expected error for too many categories"
        assert "between 0 and 5" in stderr_output, "Expected error for out of range value"
        assert "at least one category" in stderr_output, "Expected error for all zeros"

    def test_invalid_quality_rating_does_not_break_upload(self, env):
        """Test that invalid quality rating doesn't prevent result upload"""
        env.file = Path(__file__).parent / "test_data/XML/quality_rating_invalid.xml"
        parser = JunitParser(env)
        suites = parser.parse_file()

        # Parser should succeed
        assert len(suites) == 1

        # All tests should have valid results (minus quality rating)
        for section in suites[0].testsections:
            for test_case in section.testcases:
                result_dict = test_case.result.to_dict()

                # Should have basic result fields
                assert "case_id" in result_dict
                assert "status_id" in result_dict

                # Quality rating should not be present (invalid)
                assert "quality_rating" not in result_dict

    # ========== Edge Cases ==========

    def test_quality_rating_with_zero_values(self, env, tmp_path):
        """Test quality rating with some zero values (valid if at least one >= 1)"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Test" tests="1" failures="0" errors="0" time="1.0">
  <testsuite name="Suite" tests="1" failures="0" errors="0" time="1.0">
    <testcase classname="test.Test" name="test_zero_values" time="1.0">
      <properties>
        <property name="test_id" value="C300"/>
        <property name="quality_rating" value='{"accuracy": 5, "speed": 0, "reliability": 0}'/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_zero_values.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        assert test_case.result.quality_rating == {"accuracy": 5, "speed": 0, "reliability": 0}

    def test_quality_rating_maximum_15_categories(self, env, tmp_path):
        """Test quality rating with exactly 15 categories (maximum allowed)"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Test" tests="1" failures="0" errors="0" time="1.0">
  <testsuite name="Suite" tests="1" failures="0" errors="0" time="1.0">
    <testcase classname="test.Test" name="test_max_categories" time="1.0">
      <properties>
        <property name="test_id" value="C301"/>
        <property name="quality_rating" value='{"cat1": 5, "cat2": 4, "cat3": 3, "cat4": 2, "cat5": 1, "cat6": 5, "cat7": 4, "cat8": 3, "cat9": 2, "cat10": 1, "cat11": 5, "cat12": 4, "cat13": 3, "cat14": 2, "cat15": 1}'/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_max_categories.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        assert test_case.result.quality_rating is not None
        assert len(test_case.result.quality_rating) == 15

    def test_quality_rating_unicode_category_names(self, env, tmp_path):
        """Test quality rating with unicode category names"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Test" tests="1" failures="0" errors="0" time="1.0">
  <testsuite name="Suite" tests="1" failures="0" errors="0" time="1.0">
    <testcase classname="test.Test" name="test_unicode" time="1.0">
      <properties>
        <property name="test_id" value="C302"/>
        <property name="quality_rating" value='{"précision": 5, "velocità": 4, "信頼性": 3}'/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_unicode.xml"
        xml_file.write_text(xml_content, encoding="utf-8")

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        assert test_case.result.quality_rating == {"précision": 5, "velocità": 4, "信頼性": 3}

    # ========== Backward Compatibility ==========

    def test_backward_compatibility_no_quality_rating(self, env, tmp_path):
        """Test that tests without quality rating still work (backward compatibility)"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Test" tests="1" failures="0" errors="0" time="1.0">
  <testsuite name="Suite" tests="1" failures="0" errors="0" time="1.0">
    <testcase classname="test.Test" name="test_no_rating" time="1.0">
      <properties>
        <property name="test_id" value="C400"/>
        <property name="testrail_result_field" value="custom_field:value"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_backward_compat.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result_dict = test_case.result.to_dict()

        # Should not have quality_rating key (skip_if_default=True)
        assert "quality_rating" not in result_dict

        # Should still have other fields
        assert "case_id" in result_dict
        assert "status_id" in result_dict
        assert "custom_field" in result_dict

    # ========== Step-Level Results with Quality Rating ==========

    def test_step_level_results_with_quality_rating(self, env, tmp_path):
        """Test AI Evaluation with step-level results and overall quality rating"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="AI Tests" tests="1" failures="1" errors="0" time="10.0">
  <testsuite name="Multi-Step AI Workflow" tests="1" failures="1" errors="0" time="10.0">
    <testcase classname="ai.RAGPipeline" name="C500_test_rag_pipeline" time="10.0">
      <properties>
        <property name="test_id" value="C500"/>
        <property name="testrail_result_step" value="passed:Step 1 Query Understanding"/>
        <property name="testrail_result_step" value="passed:Step 2 Document Retrieval"/>
        <property name="testrail_result_step" value="failed:Step 3 Answer Generation"/>
        <property name="testrail_result_step" value="untested:Step 4 Response Validation"/>
        <property name="quality_rating" value='{"factual_accuracy": 2, "coherence": 3, "completeness": 1}'/>
        <property name="testrail_result_field" value="custom_ai_input:What is Python?"/>
        <property name="testrail_result_field" value="custom_ai_output:Python is a snake..."/>
      </properties>
      <failure message="Answer generation produced factually incorrect response"/>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_step_level_quality.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result = test_case.result

        # Verify step-level results
        assert len(result.custom_step_results) == 4
        assert result.custom_step_results[0].content == "Step 1 Query Understanding"
        assert result.custom_step_results[0].status_id == 1  # Passed
        assert result.custom_step_results[1].content == "Step 2 Document Retrieval"
        assert result.custom_step_results[1].status_id == 1  # Passed
        assert result.custom_step_results[2].content == "Step 3 Answer Generation"
        assert result.custom_step_results[2].status_id == 5  # Failed
        assert result.custom_step_results[3].content == "Step 4 Response Validation"
        assert result.custom_step_results[3].status_id == 3  # Untested

        # Verify overall quality rating
        assert result.quality_rating == {"factual_accuracy": 2, "coherence": 3, "completeness": 1}

        # Verify overall test status is failed
        assert result.status_id == 5

    def test_step_level_serialization_with_quality_rating(self, env, tmp_path):
        """Test that step-level results and quality rating serialize correctly"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="AI Tests" tests="1" failures="0" errors="0" time="5.0">
  <testsuite name="Success Flow" tests="1" failures="0" errors="0" time="5.0">
    <testcase classname="ai.ChatBot" name="C501_test_chatbot_steps" time="5.0">
      <properties>
        <property name="test_id" value="C501"/>
        <property name="testrail_result_step" value="passed:Intent Detection"/>
        <property name="testrail_result_step" value="passed:Response Generation"/>
        <property name="testrail_result_step" value="passed:Quality Check"/>
        <property name="quality_rating" value='{"accuracy": 5, "relevance": 5, "tone": 4}'/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_step_serialization.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result_dict = test_case.result.to_dict()

        # Verify custom_step_results serialization
        assert "custom_step_results" in result_dict
        assert len(result_dict["custom_step_results"]) == 3
        assert result_dict["custom_step_results"][0]["content"] == "Intent Detection"
        assert result_dict["custom_step_results"][0]["status_id"] == 1
        assert result_dict["custom_step_results"][1]["content"] == "Response Generation"
        assert result_dict["custom_step_results"][1]["status_id"] == 1
        assert result_dict["custom_step_results"][2]["content"] == "Quality Check"
        assert result_dict["custom_step_results"][2]["status_id"] == 1

        # Verify quality_rating at root level
        assert "quality_rating" in result_dict
        assert result_dict["quality_rating"] == {"accuracy": 5, "relevance": 5, "tone": 4}

    def test_step_level_mixed_statuses(self, env, tmp_path):
        """Test step-level results with various status combinations"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="AI Tests" tests="1" failures="0" errors="0" time="3.0">
  <testsuite name="Partial Success" tests="1" failures="0" errors="0" time="3.0">
    <testcase classname="ai.Pipeline" name="C502_test_mixed_steps" time="3.0">
      <properties>
        <property name="test_id" value="C502"/>
        <property name="testrail_result_step" value="passed:Pre-processing"/>
        <property name="testrail_result_step" value="skipped:Optional Enhancement"/>
        <property name="testrail_result_step" value="passed:Final Output"/>
        <property name="quality_rating" value='{"quality": 4}'/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_mixed_steps.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result = test_case.result

        # Verify all step statuses
        assert len(result.custom_step_results) == 3
        assert result.custom_step_results[0].status_id == 1  # Passed
        assert result.custom_step_results[1].status_id == 4  # Skipped
        assert result.custom_step_results[2].status_id == 1  # Passed

        # Overall test should pass (no failures)
        assert result.status_id == 1

        # Quality rating should be preserved
        assert result.quality_rating == {"quality": 4}

    def test_step_level_without_quality_rating(self, env, tmp_path):
        """Test that step-level results work without quality rating (backward compatibility)"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Tests" tests="1" failures="0" errors="0" time="2.0">
  <testsuite name="Basic Steps" tests="1" failures="0" errors="0" time="2.0">
    <testcase classname="test.Steps" name="C503_test_steps_only" time="2.0">
      <properties>
        <property name="test_id" value="C503"/>
        <property name="testrail_result_step" value="passed:Step 1"/>
        <property name="testrail_result_step" value="passed:Step 2"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_steps_no_rating.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result_dict = test_case.result.to_dict()

        # Should have steps
        assert "custom_step_results" in result_dict
        assert len(result_dict["custom_step_results"]) == 2

        # Should NOT have quality_rating
        assert "quality_rating" not in result_dict

    def test_quality_rating_without_steps(self, env, tmp_path):
        """Test that quality rating works without step-level results"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="Tests" tests="1" failures="0" errors="0" time="1.0">
  <testsuite name="No Steps" tests="1" failures="0" errors="0" time="1.0">
    <testcase classname="test.Simple" name="C504_test_quality_only" time="1.0">
      <properties>
        <property name="test_id" value="C504"/>
        <property name="quality_rating" value='{"accuracy": 5}'/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""

        xml_file = tmp_path / "test_rating_no_steps.xml"
        xml_file.write_text(xml_content)

        env.file = xml_file
        parser = JunitParser(env)
        suites = parser.parse_file()

        test_case = suites[0].testsections[0].testcases[0]
        result_dict = test_case.result.to_dict()

        # Should have quality_rating
        assert "quality_rating" in result_dict
        assert result_dict["quality_rating"] == {"accuracy": 5}

        # Should NOT have custom_step_results (empty list skipped by serialization)
        assert "custom_step_results" not in result_dict or result_dict["custom_step_results"] == []

    def test_parse_sample_multistep_workflow(self, env):
        """Test parsing the sample multi-step AI evaluation workflow file"""
        env.file = Path(__file__).parent / "test_data/XML/sample_ai_eval_multistep_workflow.xml"
        parser = JunitParser(env)
        suites = parser.parse_file()

        assert len(suites) == 1
        suite = suites[0]
        assert len(suite.testsections) == 1
        section = suite.testsections[0]
        assert len(section.testcases) == 3

        # Test 1: All steps pass
        test1 = section.testcases[0]
        assert test1.result.case_id == 1000
        assert test1.result.status_id == 1  # Passed
        assert len(test1.result.custom_step_results) == 4
        assert all(step.status_id == 1 for step in test1.result.custom_step_results)  # All passed
        assert test1.result.quality_rating == {
            "factual_accuracy": 5,
            "coherence": 5,
            "completeness": 4,
            "relevance": 5,
        }

        # Test 2: Step 3 fails
        test2 = section.testcases[1]
        assert test2.result.case_id == 1001
        assert test2.result.status_id == 5  # Failed
        assert len(test2.result.custom_step_results) == 4
        assert test2.result.custom_step_results[0].status_id == 1  # Step 1 passed
        assert test2.result.custom_step_results[1].status_id == 1  # Step 2 passed
        assert test2.result.custom_step_results[2].status_id == 5  # Step 3 failed
        assert test2.result.custom_step_results[3].status_id == 3  # Step 4 untested
        assert test2.result.quality_rating == {
            "factual_accuracy": 1,
            "coherence": 3,
            "completeness": 2,
            "relevance": 2,
        }

        # Test 3: Step 2 fails
        test3 = section.testcases[2]
        assert test3.result.case_id == 1002
        assert test3.result.status_id == 5  # Failed
        assert len(test3.result.custom_step_results) == 4
        assert test3.result.custom_step_results[0].status_id == 1  # Step 1 passed
        assert test3.result.custom_step_results[1].status_id == 5  # Step 2 failed
        assert test3.result.custom_step_results[2].status_id == 3  # Step 3 untested
        assert test3.result.custom_step_results[3].status_id == 3  # Step 4 untested
        assert test3.result.quality_rating == {
            "factual_accuracy": 0,
            "coherence": 1,
            "completeness": 0,
            "relevance": 1,
        }
