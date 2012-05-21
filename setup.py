#!/usr/bin/env python

from setuptools import setup, find_packages

entry_points = {
	'console_scripts': [
		"nti_render = nti.contentrendering.nti_render:main",
		"nti_init_env = nti.dataserver.config:main",
		"nti_pubsub_device = nti.dataserver._PubSubDevice:main",
		"nti_cache_avatars = nti.dataserver.utils.nti_cache_avatars:main",
		"nti_create_user = nti.dataserver.utils.nti_create_user:main",
		"nti_remove_user = nti.dataserver.utils.nti_remove_user:main",
		"nti_sharing_listener = nti.appserver.application:sharing_listener_main",
		"nti_index_listener = nti.appserver.application:index_listener_main",
		"nti_reindex_user_content = nti.contentsearch.utils.nti_reindex_user_content:main",
		"nti_remove_user_content = nti.contentsearch.utils.nti_remove_user_content:main"
	],
	"paste.app_factory": [
		"main = nti.appserver.standalone:configure_app",
		"gunicorn = nti.appserver.gunicorn:dummy_app_factory"
	],

	"paste.filter_app_factory": [
		"cors = nti.appserver.cors:cors_filter_factory"
	],
	"paste.server_runner": [
		"http = nti.appserver.standalone:server_runner"
	],
	"nose.plugins.0.10" : [
		"zopeexceptionlogpatch = nti.tests:ZopeExceptionLogPatch"
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
	install_requires = [
		'RestrictedPython',
		'ZODB3',
		# ZODB RelStorage:
		# 'pylibmc', # for memcached support
		# 'MySQL-python', # mysql adapter
		# 'RelStorage',
		'anyjson',
		'boto >= 2.4.1', # amazon
		'brownie',
		'coverage',
		'cython',
		'futures >= 2.1.2',
		#'gevent == 1.0dev', Coming from requirements.txt right now
		'gevent-zeromq',
		'gunicorn == 0.14.2',
		'html5lib == 0.95',
		'logilab-common',
		'nltk',
		'paste',
		'pyhamcrest',
		'pylint',
		'pyquery >= 1.2',
		'pyramid >= 1.3' ,
		'pyramid_tm',
		'pyramid_traversalwrapper',
		'pyramid_who',
		'pyramid_zcml >= 0.9.2',
		'pyramid_zodbconn >= 0.3',
		'pyramid-openid',
		'pytz',
		'rdflib',
		'repoze.catalog',
		'repoze.sphinx.autointerface',
		'repoze.who',
		'repoze.zodbconn',
		'requests >= 0.12.1',
		'scss',
		'setproctitle',
		'setuptools',
		'simplejson',
		'sympy == 0.7.1', # sympy-docs-html-0.7.1 is currently greater
		'six',
		'slimit',
		'supervisor',
		'transaction >= 1.2.0',
		'webob',
		'webtest',
		'whoosh == 2.3.2',
		 # bcrypt/pbkdf2 for zope.password
		 # adds cryptacular and pbkdf2
		'z3c.bcrypt',
		'z3c.coverage',
		'z3c.pt', # Better ZPT support than plastex
		'zc.queue',
		'zc.zlibstorage', # compressed records. Will be built-in to newer ZODB
		'zetalibrary',
		'zope.annotation',
		'zope.broken',
		'zope.browser',
		'zope.browserpage',
		'zope.browserresource',
		'zope.component >= 3.12.1',
		'zope.componentvocabulary',
		'zope.configuration',
		'zope.container',
		'zope.contenttype',
		'zope.copy >= 3.5.0',
		'zope.datetime',
		'zope.dottedname',
		'zope.event',
		'zope.exceptions',
		'zope.filerepresentation',
		'zope.formlib',
		'zope.generations',
		'zope.i18n',
		'zope.i18nmessageid',
		'zope.interface >= 3.8.0',
		'zope.lifecycleevent',
		'zope.location',
		'zope.mimetype',
		'zope.minmax >= 1.1.2',
		'zope.pagetemplate',
		'zope.password', # encrypted password management
		'zope.publisher',
		'zope.processlifetime',
		'zope.schema',
		'zope.security',
		'zope.site',
		'zope.size',
		'zope.tal',
		'zope.tales',
		'zope.testing',
		'zope.traversing',
		# textindexng3
		'zopyx.txng3.core',
		'zopyx.txng3.ext',
		],
	extras_require = {'test': ['zope.testing', 'zc.buildout', 'selenium'], 'tools': ['ipython', 'httpie']},
	dependency_links = ['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
	packages = find_packages('src'),
	package_dir = {'': 'src'},
	include_package_data = True,
	namespace_packages=['nti',],
	zip_safe = False,
	entry_points = entry_points
	)
