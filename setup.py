#! /usr/bin/env python
#
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from gview.version import version
import os

srcdir = os.path.dirname(__file__)

from distutils.command.build_py import build_py

def read(fname):
    try:
        buf = open(os.path.join(srcdir, fname), 'r').read()
    except Exception:
        buf = "gview simple astronomical image viewer"
    return buf


setup(
    name = "gview",
    version = version,
    author = "Eric Jeschke",
    author_email = "eric@naoj.org",
    description = ("A simple astronomical image viewer modeled after ZVIEW."),
    long_description = read('README.txt'),
    license = "BSD",
    keywords = "image viewer astronomy FITS",
    url = "http://naojsoft.github.com/gview",
    packages = ['gview',
                ],
    package_data = {},
    scripts = ['scripts/gview'],
    install_requires = ['ginga>=2.5'],
    classifiers=[
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: C',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Astronomy',
          'Topic :: Scientific/Engineering :: Physics',
          ],
    cmdclass={'build_py': build_py}
)
