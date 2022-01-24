from pathlib import Path

correct_yaml_expected_result = dict(
    host="https://fakename.testrail.io/",
    project="Project name",
    file="result.xml",
    title="Project title",
    verbose=False,
    silent=False,
    batch_size=20,
    timeout=50,
    auto_creation_response=True,
    suite_id=50,
    run_id=10,
)
correct_config_file_path = Path(__file__).parent / "yaml" / "correct_config_file.yaml"
correct_config_file_path_with_custom_config_path = (
    Path(__file__).parent / "yaml" / "correct_config_file_with_custom_config_path.yaml"
)
correct_config_file_loop_check_path = (
    Path(__file__).parent / "yaml" / "correct_config_file_loop_check.yaml"
)
correct_config_file_multiple_documents_path = (
    Path(__file__).parent / "yaml" / "correct_config_file_multiple_documents.yaml"
)
correct_config_file_multiple_documents_path_with_custom_config_path = (
    Path(__file__).parent
    / "yaml"
    / "correct_config_file_multiple_documents_with_custom_config_path.yaml"
)
incorrect_config_file_path = (
    Path(__file__).parent / "yaml" / "corrupted_config_file.yaml"
)
incorrect_config_file_multiple_documents_path = (
    Path(__file__).parent / "yaml" / "corrupted_config_file_multiple_documents.yaml"
)
