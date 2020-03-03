import os
import re

from setuptools import setup, find_packages

ROOT = os.path.dirname(__file__)
VERSION_RE = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')


def get_version():
    init = open(os.path.join(ROOT, 'stax', '__init__.py')).read()
    return VERSION_RE.search(init).group(1)


setup(
    name='stax',
    description=
    'Stax is a Python tool to manage every aspect of Cloudformation Stacks',
    version=get_version(),
    license='MIT',
    install_requires=[
        'GitPython',
        'PyYAML',
        'boto3',
        'click',
    ],
    url='https://github.com/acaire/stax',
    packages=find_packages(exclude=['tests*']),
    author='Ash Caire',
    author_email='ash.caire@gmail.com',
    keywords=[
        'stack',
        'stacks',
        'aws',
        'cloudformation',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
    ],
    entry_points='''
        [console_scripts]
        stax=stax.stax:cli
    ''',
)
