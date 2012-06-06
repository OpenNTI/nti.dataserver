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
		"nti_delete_user_objects = nti.dataserver.utils.nti_delete_user_objects:main",
		"nti_export_user_objects = nti.dataserver.utils.nti_export_user_objects:main",
		"nti_sharing_listener = nti.appserver.application:sharing_listener_main",
		"nti_index_listener = nti.appserver.application:index_listener_main",
		"nti_reindex_user_content = nti.contentsearch.utils.nti_reindex_user_content:main",
		"nti_remove_user_search_content = nti.contentsearch.utils.nti_remove_user_content:main"
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
		'Chameleon >= 2.9.1',
		'RestrictedPython',
		'ZODB3 >= 3.10.5',
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
		'gunicorn >= 0.14.3',
		'html5lib == 0.95',
		 # WSGI middleware for profiling. Defaults to storing
		 # data in a sqlite file. Works across multiple gunicorn workers, does
		 # OK with websockets and greenlets. Needs trivial patch to work (display results) with
		 # webob 1.2, collects data ok without patch.
		 # Depends on the system graphviz installation; an alternative is repoze.profile which has
		 # fewer dependencies, but less helpful output and doesn't work with multiple workers (?)
		'linesman >= 0.2.2',
		'logilab-common',
		'nltk',
		'paste',
		'pyhamcrest',
		'pylint',
		'pyquery >= 1.2',
		'pyramid >= 1.3.2' ,
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
		'grequests >= 0.1.0', #replaces requests.async in 0.13
		'requests >= 0.13.0', # HTTP
		'scss',
		'setproctitle',
		'setuptools',
		'simplejson',
		'sympy == 0.7.1', # sympy-docs-html-0.7.1 is currently greater
		'six',
		'slimit',
		'supervisor',
		'transaction >= 1.3.0',
		'webob >= 1.2',
		'webtest >= 1.3.4',
		'whoosh == 2.3.2',
		 # bcrypt/pbkdf2 for zope.password
		 # adds cryptacular and pbkdf2
		'z3c.bcrypt',
		'z3c.coverage',
		'z3c.pt', # Better ZPT support than plastex, add-in to Chameleon
		'zc.queue >= 1.3',
		'zc.zlibstorage', # compressed records. Will be built-in to newer ZODB
		'zc.zodbdgc',
		'zetalibrary',
		'zope.annotation',
		'zope.broken',
		'zope.browser',
		'zope.browserpage',
		'zope.browserresource',
		'zope.component >= 3.12.1',
		'zope.componentvocabulary',
		'zope.configuration >= 4.0.0',
		'zope.container >= 3.12.0',
		'zope.contenttype >= 3.5.5',
		'zope.copy >= 3.5.0',
		'zope.datetime',
		'zope.deprecation >= 4.0.0',
		'zope.dottedname',
		'zope.event >= 4.0.0',
		'zope.exceptions >= 4.0.0.1',
		'zope.filerepresentation',
		'zope.formlib',
		'zope.generations >= 3.7.1',
		'zope.hookable >= 4.0.0', # explicitly list this to ensure we get the fast C version. Used by ZCA.
		'zope.i18n',
		'zope.i18nmessageid',
		'zope.interface >= 4.0.1',
		'zope.lifecycleevent >= 3.7.0',
		'zope.location >= 3.9.1',
		'zope.mimetype',
		'zope.minmax >= 1.1.2',
		'zope.pagetemplate',
		'zope.password', # encrypted password management
		'zope.publisher',
		'zope.processlifetime',
		'zope.schema >= 4.2.0',
		'zope.security >= 3.8.3',
		'zope.site',
		'zope.size >= 3.5.0',
		'zope.tal',
		'zope.tales',
		'zope.testing',
		'zope.traversing >= 3.14.0',
		# textindexng3
		'zopyx.txng3.core',
		'zopyx.txng3.ext',
		],
	extras_require = {'test': ['zope.testing', 'zc.buildout', 'selenium'],
					  'tools': [
						  'dblatex >= 0.3.4', # content rendering, convert docbook to tex
						  'ipython',
						  'httpie']},
	dependency_links = ['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
	packages = find_packages('src'),
	package_dir = {'': 'src'},
	include_package_data = True,
	namespace_packages=['nti',],
	zip_safe = False,
	entry_points = entry_points
	)
