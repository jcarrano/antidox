from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='antidox',
      version='0.2.1',
      description='Sphinx extension to extract and insert Doxygen documentation.',
      long_description=readme(),
      long_description_content_type='text/x-rst',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'Framework :: Sphinx :: Extension',
        'Topic :: Documentation :: Sphinx',
        'Topic :: Software Development :: Documentation'
      ],
      keywords='sphinx doxygen',
      url='https://github.com/jcarrano/antidox',
      project_urls={
        'Documentation': 'https://antidox.readthedocs.io/en/latest/index.html',
        'Tracker': 'https://github.com/jcarrano/antidox/issues',
      },
      author='Juan I Carrano <juan@carrano.com.ar>',
      author_email='juan@carrano.com.ar',
      license='BSD',
      packages=['antidox'],
      install_requires=[
        'sphinx>=3.3.1,<3.5',
        'lxml'
      ],
      entry_points={
        'console_scripts': [
            'antidox-shell = antidox.shell:main',
        ],
      },
      include_package_data=True,
      zip_safe=True
)
