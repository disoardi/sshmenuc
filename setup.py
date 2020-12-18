from setuptools import setup

with open('requirements.txt') as requirements_file:
    required = requirements_file.read().splitlines()

setup(
    name='sshmenuC',
    version='0.0.4',
    license='MIT',
    description='Command line SSH menu and helper utility with cluster support',
    long_description=open('README.md').read(),
    author='Davide Isoardi',
    author_email='davide@isoardi.info',
    url='https://github.com/disoardi/sshmenu',
    packages=['sshmenuc'],
    install_requires=required,
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],
    entry_points={
        'console_scripts': ['sshmenuc=sshmenu.sshmenu:main']
    }
)
