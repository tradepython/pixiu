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
    'TA-Lib',
    'pymongo',
    'tabulate',
    'hashids'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',
    'pytest-cov',
]

setup(
    name='pixiu',
    version='0.76.0',
    description='PiXiu - A trading backtesting tool similar to MT4/MT5',
    long_description=README + '\n\n' + CHANGES,
    long_description_content_type="text/markdown",
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License'
    ],
    author='tradepython',
    author_email='tradepython@icloud.com',
    url='https://github.com/tradepython/pixiu',
    project_urls={
        "Bug Tracker": "https://github.com/tradepython/pixiu/issues",
    },
    keywords='Trading Backtest Forex Stocks MT4 MT5 MetaTrade',
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
    python_requires=">=3.8",
)
