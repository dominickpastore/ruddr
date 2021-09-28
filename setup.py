from setuptools import setup, find_packages

with open("README.rst", "r") as f:
    long_description = f.read()

setup(
    name='ruddr',
    version='0.1.0',
    author='Dominick C. Pastore',
    author_email='dominickpastore@dcpx.org',
    description='Robotic Updater for Dynamic DNS Records',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/dominickpastore/ruddr/',
    license='Copyright (c) 2021 Dominick C. Pastore. All rights reserved.',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Topic :: Internet :: Name Service (DNS)",
    ],

    packages=find_packages(),
    install_requires=[
        'requests',
        'netifaces',
    ],
    python_requires='>=3.6',
    extras_require={
        'systemd': ['systemd'],
        'networkd': ['PyGObject'],
    },

    entry_points={
        'console_scripts': [
            'ruddr=ruddr.manager:main',
        ],
    },
)
