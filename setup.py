from setuptools import setup
from trcli import __version__

setup(
    name="trcli",
    version=__version__,
    packages=["trcli", "trcli.commands"],
    include_package_data=True,
    install_requires=["click", "requests"],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
