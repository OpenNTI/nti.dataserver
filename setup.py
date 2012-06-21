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
	],
	"zodbupdate" : [ # Migrating class names through zodbupdate >= 0.5
		"chatserver_meetings = nti.chatserver.meeting:_bwc_renames"
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
		'Chameleon >= 2.9.2',
		'RestrictedPython',
		'ZODB3 >= 3.10.5',
		# ZODB RelStorage:
		# 'pylibmc', # for memcached support
		# 'MySQL-python', # mysql adapter
		# 'RelStorage',
		'anyjson >= 0.3.1',
		'boto >= 2.5.2', # amazon
		'brownie >= 0.5.1', # Common utilities
		'coverage >= 3.5.2', # Test coverage
		'cssselect >= 0.7.1', # Used by pyquery
		'cython >= 0.16',
		# support for defining and evolving classes based on schemas
		# pulls in dm.reuse
		'dm.zope.schema >= 2.0',
		'dolmen.builtins >= 0.3.1', # interfaces for common python types
		'futures >= 2.1.2',
		#'gevent == 1.0dev', Coming from requirements.txt right now
		# NOTE: gevent_zeromq and pyzmq are tightly coupled. Updating pyzmq
		# usually requires rebuilding gevent_zeromq. You'll get errors about 'Context has wrong size'.
		# You may be able to fix it with 'pip install -U --force --no-deps gevent_zeromq'. You may not;
		# if that doesn't work, the solution is to download gevent_zeromq manually, untar it, and
		# run 'python setup.py install'. It may be necessary to 'pip uninstall' this (and/or remove it from zite-packages)
		# before running setup.py.
		# NOTE2: This will go away soon, merged into pyzmq 2.2dev as zmq.green
		'gevent_zeromq >= 0.2.2',
		'greenlet >= 0.4.0',
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
		'nltk >= 2.0.1',
		# numpy is req'd by nltk, but not depended on. sigh.
		# This turns out to be because it CANNOT be installed in a setup.py:
		# Apparently it ships its own distutils. If you try to install from setup.py, you get
		# Warning: distutils distribution has been initialized, it may be too late to add a subpackage command
		# followed by compilation failures: fatal error 'Python.h' file not found. So you must
		# install numpy manually with pip: pip install numpy
		'numpy >= 1.6.2',
		'paste',
		'pyhamcrest',
		'pylint',
		'pyquery >= 1.2.1', # jquery-like traversing of python datastructures. lxml, cssselect
		'pyramid >= 1.3.2' ,
		'pyramid_tm',
		'pyramid_traversalwrapper',
		'pyramid_who',
		'pyramid_zcml >= 0.9.2',
		'pyramid_zodbconn >= 0.3',
		'pyramid-openid',
		# Best if the system has ZMQ >= 2.2.0. Can work as far back as 2.1.7 (at least). 2.1.10 or better recommended;
		# I (JAM) *think* the ZMQ libs are all binary compatible so you can upgrade from 2.1 to 2.2
		# on the fly without touching the python level.
		# You may have to install this manually, depending on where zmq is installed.
		# something like:
		# pip install --install-option="--zmq=/opt/nti" pyzmq
		'pyzmq >= 2.2.0',
		'pytz',
		'rdflib',
		'repoze.catalog',
		'repoze.sphinx.autointerface >= 0.6.2',
		'repoze.who >= 2.0',
		'repoze.zodbconn >= 0.14',
		'grequests >= 0.1.0', #replaces requests.async in 0.13
		'requests >= 0.13.1', # HTTP
		'scss',
		'setproctitle',
		'setuptools',
		'simplejson >= 2.5.2',
		'sympy == 0.7.1', # sympy-docs-html-0.7.1 is currently greater
		'six >= 1.1.0',
		'slimit',
		'supervisor >= 3.0a12',
		'transaction >= 1.3.0',
		'webob >= 1.2',
		'webtest >= 1.3.4',
		'whoosh == 2.3.2',
		 # bcrypt/pbkdf2 for zope.password
		 # adds cryptacular and pbkdf2
		'z3c.bcrypt >= 1.1',
		'z3c.coverage >= 1.2.0', # TODO: Do we need this?
		'z3c.pt >= 2.2.3', # Better ZPT support than plastex, add-in to Chameleon
		'zc.intid >= 1.0.1',
		'zc.queue >= 1.3',
		'zc.zlibstorage >= 0.1.1', # compressed records. Will be built-in to newer ZODB
		'zc.zodbdgc >= 0.6.0',
		'zetalibrary',
		'zope.annotation >= 3.5.0',
		'zope.broken',
		'zope.browser',
		'zope.browserpage',
		'zope.browserresource',
		'zope.component >= 3.12.1',
		'zope.componentvocabulary',
		'zope.configuration >= 4.0.0',
		'zope.container >= 3.12.0',
		'zope.contenttype >= 3.5.5',
		'zope.copy >= 4.0.0',
		'zope.datetime >= 3.4.1',
		'zope.deprecation >= 4.0.0',
		'zope.dottedname >= 3.4.6',
		'zope.event >= 4.0.0',
		'zope.exceptions >= 4.0.0.1',
		'zope.filerepresentation',
		'zope.formlib',
		'zope.generations >= 3.7.1',
		'zope.hookable >= 4.0.0', # explicitly list this to ensure we get the fast C version. Used by ZCA.
		'zope.i18n',
		'zope.i18nmessageid',
		'zope.interface >= 4.0.1',
		'zope.intid >= 3.7.2',
		'zope.lifecycleevent >= 3.7.0',
		'zope.location >= 4.0.0',
		'zope.mimetype >= 1.3.1',
		'zope.minmax >= 1.1.2',
		'zope.pagetemplate',
		'zope.password', # encrypted password management
		'zope.publisher',
		'zope.processlifetime',
		'zope.schema >= 4.2.0',
		'zope.security >= 3.8.3',
		'zope.site >= 3.9.2', # local, persistent ZCA sites
		'zope.size >= 3.5.0',
		'zope.tal',
		'zope.tales',
		'zope.testing >= 4.1.1',
		'zope.traversing >= 3.14.0',
		# textindexng3
		'zopyx.txng3.core',
		'zopyx.txng3.ext',
		],
	extras_require = {
		'test': [
			'zope.testing',
			'zc.buildout',
			'nose-progressive',
			'fudge'],
		'tools': [
			'dblatex >= 0.3.4', # content rendering, convert docbook to tex
			'ipython',
			'readline',
			'httpie',
			'zodbupdate >= 0.5'
			]
	},
	dependency_links = ['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
	packages = find_packages('src'),
	package_dir = {'': 'src'},
	include_package_data = True,
	namespace_packages=['nti',],
	zip_safe = False,
	entry_points = entry_points
	)
