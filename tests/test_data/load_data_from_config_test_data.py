from pathlib import Path

correct_yaml_expected_result = dict(
    host="https://fakename.testrail.io/",
    project="Project name",
    file="result.xml",
    title="Project title",
    verbose=False,
    silent=False,
    config="custom_config.yaml",
    batch_size=20,
    timeout=50,
    auto_creation_response=True,
    suite_id=50,
    run_id=10,
)
correct_config_file_path = (
    Path(__file__).parent / "yaml" / "correct_config_file.yaml"
)
incorrect_config_file_path = (
    Path(__file__).parent / "yaml" / "corrupted_config_file.yaml"
)
