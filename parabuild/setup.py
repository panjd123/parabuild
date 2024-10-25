from setuptools import setup, find_packages

setup(
    name="parabuild",
    version="0.1.0",
    packages=find_packages(),
    description="",
    long_description=open("../README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="panjd123",
    author_email="xm.jarden@gmail.com",
    license="MIT",
    url="https://github.com/panjd123/parabuild",
    install_requires=[
        "tqdm",
    ],
)
