from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="protocol-converter",
    version="1.0.0",
    author="Protocol Converter Team",
    author_email="team@protocolconverter.com",
    description="A universal protocol conversion system based on Jinja2 templates",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/protocolconverter/protocol-converter",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "protocol-converter=protocol_converter.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "protocol_converter": ["examples/**/*.json"],
    },
)