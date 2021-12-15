from setuptools import setup

setup(
    name="trcli",
    version=__version__,
    packages=["trcli", "trcli.commands"],
    include_package_data=True,
    install_requires=["click", "junitparser", "pyserde"],
    entry_points="""
        [console_scripts]
        trcli=trcli.cli:cli
    """,
)
