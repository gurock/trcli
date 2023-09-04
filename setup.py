from setuptools import setup
from trcli import __version__

setup(
    name="trcli",
    long_description="The TR CLI (trcli) is a command line tool for interacting with TestRail and uploading test automation results.",
    version=__version__,
    packages=[
        "trcli",
        "trcli.commands",
        "trcli.readers",
        "trcli.data_providers",
        "trcli.data_classes",
        "trcli.api",
    ],
    include_package_data=True,
    install_requires=[
        "click==8.0.*",
        "pyyaml==6.0.*",
        "junitparser==3.1.*",
        "pyserde==0.12.*",
        "requests==2.31.*",
        "tqdm==4.65.*",
        "humanfriendly==10.0.*",
        "openapi-spec-validator==0.5.*",
        "prance"  # Does not use semantic versioning
    ],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
