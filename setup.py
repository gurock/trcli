
from setuptools import setup

setup(
    name="trcli",
    version="0.1",
    packages=["trcli", "trcli.commands"],
    include_package_data=True,
    install_requires=["click"],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
