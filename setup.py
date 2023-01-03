from setuptools import setup

setup(
    name='messplatz',
    version='0.5',
    install_requires=[
        'websockets>=10.3',
        'pyserial>=3.5',
        'numpy>=1.22.3',
        'PyQt5>=5.15.6',
        'pandas>=1.5.1',
        'ntplib>=0.4.0'
    ],
    description='TODO',
    url='TODO',
    author='Tobias Allrich',
    author_email='TODO',
    license='',
    packages=['messplatz'],
    test_suite='test'
)