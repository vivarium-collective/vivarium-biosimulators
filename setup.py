# import os
# import glob
# import setuptools
from distutils.core import setup

with open("README.md", 'r') as readme:
    long_description = readme.read()

setup(
    name='',  # TODO: Put your package name here.
    version='0.0.1',
    packages=[
        # TODO: Replace 'vivarium_tellurium' with the name of your folder.
        'vivarium_tellurium',
        'vivarium_tellurium.processes',
        'vivarium_tellurium.composites',
        'vivarium_tellurium.experiments',
    ],
    author='',  # TODO: Put your name here.
    author_email='',  # TODO: Put your email here.
    url='',  # TODO: Put your project URL here.
    license='',  # TODO: Choose a license.
    entry_points={
        'console_scripts': []},
    short_description='',  # TODO: Describe your project briefely.
    long_description=long_description,
    long_description_content_type='text/markdown',
    package_data={},
    include_package_data=True,
    install_requires=[
        'vivarium-core>=0.3.4',
        'biosimulators-tellurium>=0.1.18',
        'biosimulators-utils>=0.1.116',
    ],
    tests_require=[
        'pytest',
    ],
)
