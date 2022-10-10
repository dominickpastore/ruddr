from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name='ruddr',
    version='0.0.0dev0',
    author='Dominick C. Pastore',
    author_email='dominickpastore@dcpx.org',
    description='Robotic Updater for Dynamic DNS Records',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/dominickpastore/ruddr/',
    license='Copyright (c) 2022 Dominick C. Pastore. All rights reserved.',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Topic :: Internet :: Name Service (DNS)",
    ],

    packages=find_packages(),
    install_requires=[
        'requests',
        'netifaces',
        "importlib_metadata; python_version<'3.10'",
    ],
    python_requires='>=3.7',
    extras_require={
        'systemd': ['PyGObject'],   # Systemd notifier
        'docs': ['sphinx'],
        'test': [
            'flake8',
            'pytest',
            'pytest-cov'
        ]
    },

    entry_points={
        'console_scripts': [
            'ruddr=ruddr.manager:main',
        ],
    },
)
