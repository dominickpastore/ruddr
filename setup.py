import subprocess

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

# Get version from "git describe" (requires releases to be tagged vX.Y.Z and
# initial commit to be tagged v0.0.0, both with annotated tags)
git_version = subprocess.check_output(
    ['git', 'describe', '--abbrev', '--dirty'],
    text=True,
)
version_parts = git_version.strip().lstrip('v').split('-')
version = version_parts[0]
if len(version_parts) > 1:
    version += f".dev{version_parts[1]}+{version_parts[2]}"
if len(version_parts) > 3:
    version += ".dirty"

setup(
    name="ruddr",
    version=version,
    author="Dominick C. Pastore",
    author_email="ruddr@dcpx.org",
    description="Robotic Updater for Dynamic DNS Records",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dominickpastore/ruddr/",
    license="Copyright (c) 2022 Dominick C. Pastore. All rights reserved.",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Topic :: Internet :: Name Service (DNS)",
    ],

    packages=find_packages(),
    install_requires=[
        "requests",
        "netifaces",
        "dnspython",
        "importlib_metadata; python_version<'3.10'",
    ],
    python_requires=">=3.7",
    extras_require={
        "systemd": ["PyGObject"],   # Systemd notifier
        "docs": ["sphinx"],
        "test": [
            "flake8",
            "pytest",
            "pytest-cov"
        ]
    },

    entry_points={
        "console_scripts": [
            "ruddr=ruddr.manager:main",
        ],
    },
)
