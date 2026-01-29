from setuptools import setup, find_packages

setup(
    name="automas",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "volcengine-python-sdk",
        # Add other dependencies here
    ],
)
