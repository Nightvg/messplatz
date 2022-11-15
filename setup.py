from setuptools import setup

setup(
    name='messplatz',
    version='0.5',
    install_requires=[
        'websockets>=10.3',
        'pyserial>=3.5',
        'numpy>=1.22.3'
    ],
    description='TODO',
    url='TODO',
    author='Tobias Allrich',
    author_email='TODO',
    license='',
    packages=['messplatz'],
    test_suite='test'
)