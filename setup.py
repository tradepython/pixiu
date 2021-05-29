import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.md')) as f:
    CHANGES = f.read()

requires = [
    'python-dateutil',
    'RestrictedPython',
    'numpy',
    'pandas',
    'pandas_ta',
    'TA-Lib'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',
    'pytest-cov',
]

setup(
    name='pixiu',
    version='0.30.0.20210529',
    description='PiXiu - A trading backtesting tool similar to MT4/MT5',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
    ],
    author='tradepython',
    author_email='tradepython@icloud.com',
    url='http://www.tradepython.com',
    keywords='',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'console_scripts': ['pixiu=pixiu.main:main'],
    },
)
