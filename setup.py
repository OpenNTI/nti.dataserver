#!/usr/bin/env python

from setuptools import setup, find_packages

entry_points = {
	'console_scripts': [
		"nti_render = nti.contentrendering.aopstoxml:main",
		"nti_init_env = nti.dataserver.config:main",
		"nti_pubsub_device = nti.dataserver._PubSubDevice:main"
	],
	"paste.app_factory": [
		"main = nti.appserver.standalone:configure_app"
	],

	"paste.filter_app_factory": [
		"cors = nti.appserver.cors:cors_filter_factory"
	],
	"paste.server_runner": [
		"http = nti.appserver.standalone:server_runner"
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
#	tests_require = ['z3c.coverage','zope.testing'],
	setup_requires = ['nose'],
	install_requires = [ 'supervisor',
						 'nltk',
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
						 'repoze.zodbconn',
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
						 'zope.testing',
						 'z3c.coverage',
						 'coverage',
						 'pylint'
						],
	extras_require = {'test': ['zope.testing', 'zc.buildout']},
	dependency_links = ['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
	packages = find_packages('src'),
	package_dir = {'': 'src'},
	include_package_data = True,
	namespace_packages=['nti',],
	zip_safe = False,
	entry_points = entry_points
	)
