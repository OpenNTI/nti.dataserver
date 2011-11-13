#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = 'ntids',
    version = '0.1dev',
    author = 'NTI',
    author_email = 'jason.madden@nextthought.com',
    description = 'Next Thought dataserver',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python"
        ],

    # Support unit tests of package
    test_suite = "tests",
    tests_require = ['z3c.coverage','zope.testing'],

    install_requires = [ 'setuptools',
                         'authkit',
                         'cython',
                         'gevent-zeromq',
                         'paste',
                         'pyhamcrest',
                         'pyquery',
                         'pyramid',
                         'pyramid_traversalwrapper',
                         'pyramid_zodbconn',
                         'pytz',
                         'RestrictedPython',
                         'selector',
                         'webob',
                         'whoosh',
                         'zc.queue',
                         'ZODB3',
                         'zope.browser',
                         'zope.browserpage',
                         'zope.browserresource',
                         'zope.component',
                         'zope.configuration',
                         'zope.contenttype',
                         'zope.datetime',
                         'zope.exceptions',
                         'zope.formlib',
                         'zope.i18n',
                         'zope.i18nmessageid',
                         'zope.interface',
                         'zope.lifecycleevent',
                         'zope.location',
                         'zope.mimetype',
                         'zope.pagetemplate',
                         'zope.publisher',
                         'zope.schema',
                         'zope.security',
                         'zope.tal',
                         'zope.tales',
                         'zope.traversing'
                        ],
    extras_require = {'test': ['z3c.coverage', 'zope.testing', 'zc.buildout']},

    packages = find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = False,
    zip_safe = True,
    )
