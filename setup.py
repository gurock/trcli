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
    install_requires=["click", "pyyaml", "junitparser", "pyserde", "requests", "tqdm", "humanfriendly"],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
