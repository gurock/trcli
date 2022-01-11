from setuptools import setup
from trcli import __version__

setup(
    name="trcli",
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
    install_requires=["click", "pyyaml", "junitparser", "pyserde", "requests"],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
