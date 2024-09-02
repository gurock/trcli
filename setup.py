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
        "click==8.0.3",
        "pyyaml>=6.0.0,<7.0.0",
        "junitparser>=3.1.0,<4.0.0",
        "pyserde==0.12.*",
        "requests>=2.31.0,<3.0.0",
        "tqdm>=4.65.0,<5.0.0",
        "humanfriendly>=10.0.0,<11.0.0",
        "openapi-spec-validator>=0.5.0,<1.0.0",
        "beartype>=0.17.0,<1.0.0",
        "prance"  # Does not use semantic versioning
    ],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
