import os
from setuptools import setup

VERSION = "0.0.1"
#with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.VERSION'), 'rt') as vfile:
#    VERSION = vfile.readlines()[0].strip("\n").strip()


setup(name='coiny',
      version=VERSION,
      description='Crypto portfolio tracking',
      url='https://github.com/thomasms/coiny',
      author='Tom Stainer',
      author_email='me@physicstom.com',
      license='MIT',
      packages=[
          'coiny',
      ],
      install_requires=[],
      python_requires='>=3.7',
      scripts=[
          'coiny/tools/checkaccounts.py'
      ],
      setup_requires=[
          'pytest-runner',
      ],
      test_suite='tests.testsuite',
      tests_require=[
          'pytest',
          'pytest-cov>=2.3.1',
      ],
#      package_dir={"": "coiny"},
      package_data={},
      include_package_data=True,
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'coinycheck = coiny.tools.checkaccounts:main',
          ]
      },
      )
