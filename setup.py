#!/usr/bin/env python

from setuptools import setup, find_packages

entry_points = {
	'console_scripts': [
		"nti_render = nti.contentrendering.aopstoxml:main"
	],
	"paste.app_factory": [
		"main = dataserver:main"
	],
	"paste.server_runner": [
		"http = nti.appserver.standalone:server_runner"
	],
	"dataserver": [
		"dataserver = nti.appserver.standalone:run_main"
	]
}

setup(
    name = 'nti.dataserver',
    version = '0.0',
    keywords = 'web pyramid pylons',
    author = 'NTI',
    author_email = 'jason.madden@nextthought.com',
    description = 'NextThought Dataserver',
    long_description = 'Dataserver README',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python"
        "Framework :: Pylons",
		"Internet :: WWW/HTTP",
		"Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],

    # Support unit tests of package
    tests_require = ['z3c.coverage','zope.testing'],

    install_requires = [ 'nltk',
						 'anyjson',
						 'html5lib',
						 'setuptools',
                         'authkit',
                         'cython',
                         'gevent-zeromq',
                         'gunicorn',
                         'paste',
                         'pyhamcrest',
                         'pyquery',
                         'pyramid',
                         'pyramid_traversalwrapper',
                         'pyramid_who',
                         'pyramid_zodbconn',
                         'pytz',
                         'rdflib',
                         'requests',
                         'repoze.sphinx.autointerface',
                         'repoze.who',
                         'RestrictedPython',
                         'scss',
                         'selector',
                         'setproctitle',
                         'simplejson',
                         'six',
                         'slimit',
                         'webob',
                         'webtest',
                         'whoosh',
                         'zc.queue',
                         'zetalibrary',
                         'ZODB3',
                         'zope.annotation',
                         'zope.broken',
                         'zope.browser',
                         'zope.browserpage',
                         'zope.browserresource',
                         'zope.component',
                         'zope.configuration',
                         'zope.container',
                         'zope.contenttype',
                         'zope.datetime',
                         'zope.dottedname',
                         'zope.event',
                         'zope.exceptions',
                         'zope.filerepresentation',
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
                         'zope.size',
                         'zope.tal',
                         'zope.tales',
                         'zope.traversing',
						 'zope.testing'
                        ],
    extras_require = {'test': ['z3c.coverage', 'zope.testing', 'zc.buildout']},
	dependency_links = ['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = True,
    namespace_packages=['nti',],
    zip_safe = False,
    entry_points = entry_points
    )
