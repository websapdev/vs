from setuptools import setup

setup(
    name="pytest-cov",
    version="0.0.0",
    packages=["pytest_cov"],
    entry_points={"pytest11": ["pytest_cov = pytest_cov.plugin"]},
)
