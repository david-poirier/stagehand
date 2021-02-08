import setuptools


setuptools.setup(
    name="stagehand",
    version="0.1",
    description="stagehand - a rudimentary configuration management tool",
    packages=setuptools.find_packages(
        include=[
            "stagehand",
            "stagehand.*",
        ]
    ),
    entry_points={
        "console_scripts": [
            "stagehand = stagehand.console:stagehand",
        ]
    },
    python_requires=">=3.6",
    install_requires=[
        "paramiko>=2.7.2,<3.0",
        "PyYAML>=5.4.1,<6.0",
        "wheel>=0.36.2",
    ],
)
