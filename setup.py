from setuptools import setup

setup(
    name='messplatz',
    version='0.9',
    install_requires=[
        'websocket-client>=1.4.2',
        'pyserial>=3.5',
        'numpy>=1.22.3',
        'PyQt5>=5.15.6',
        'pandas>=1.5.2',
        'ntplib>=0.4.0'
    ],
    description='TODO',
    url='TODO',
    author='Tobias Allrich',
    author_email='TODO',
    license='MIT',
    packages=['messplatz'],
    test_suite='tests'
)