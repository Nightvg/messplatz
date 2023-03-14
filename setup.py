from setuptools import setup

setup(
    name='messplatz',
    version='0.95',
    install_requires=[
        'pyserial>=3.5',
        'numpy>=1.22.3',
        'pandas>=1.5.2'
    ],
    description='''
        Software to read data in specified data format from a measuering unit, decode
        and send it to a HTTP API as POST request (push method) and save it to file.
    ''',
    url='TODO',
    author='Tobias Allrich',
    author_email='tobias.allrich@enas.fraunhofer.de',
    license='MIT',
    packages=['messplatz'],
    test_suite='tests'
)