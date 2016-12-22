#!/usr/bin/env python
from setuptools import setup, find_packages

entry_points = {
	'console_scripts': [
		# library
		"nti_s3put = nti.contentlibrary.nti_s3put:main",
		"nti_sync_all_libraries = nti.app.contentlibrary.scripts.nti_sync_all_libraries:main",
		"nti_sync_library_assets = nti.app.contentlibrary.scripts.nti_sync_library_assets:main",
		"nti_remove_package_inaccessible_assets = nti.app.contentlibrary.scripts.nti_remove_package_inaccessible_assets:main",
		# dataserver
		"nti_shards = nti.dataserver.utils.nti_shards:main",
		"nti_init_env = nti.dataserver.utils.nti_init_env:main",
		"nti_interactive = nti.dataserver.utils.nti_interactive:main",
		"nti_cache_avatars = nti.dataserver.utils.nti_cache_avatars:main",
		"nti_create_user = nti.dataserver.utils.nti_create_user:main",
		"nti_update_user = nti.dataserver.utils.nti_update_user:main",
		"nti_set_user_avatar = nti.dataserver.utils.nti_set_user_avatar:main",
		"nti_create_friendslist = nti.dataserver.utils.nti_create_friendslist:main",
		"nti_add_remove_friends = nti.dataserver.utils.nti_add_remove_friends:main",
		"nti_join_dfl = nti.dataserver.utils.nti_join_dfl:main",
		"nti_join_community = nti.dataserver.utils.nti_join_community:main",
		"nti_update_community = nti.dataserver.utils.nti_update_community:main",
		"nti_community_members = nti.dataserver.utils.nti_community_members:main",
		"nti_set_generation = nti.dataserver.utils.nti_set_generation:main",
		"nti_set_password = nti.dataserver.utils.nti_set_password:main",
		"nti_site_ops = nti.dataserver.utils.nti_site_ops:main",
		"nti_follow_entity = nti.dataserver.utils.nti_follow_entity:main",
		"nti_remove_user = nti.dataserver.utils.nti_remove_user:main",
		"nti_export_entities = nti.dataserver.utils.nti_export_entities:main",
		# appserver
		"nti_index_listener = nti.appserver.application:index_listener_main",
		"nti_sharing_listener = nti.appserver.application:sharing_listener_main",
		# NOTE: The command line tools are deprecated. Leave the setup.py entry points
		# pointing to this package to get the deprecation notice
		'nti_bounced_email_batch = nti.appserver.bounced_email_workflow:process_sqs_messages',
		'nti_testing_mark_emails_bounced = nti.appserver.bounced_email_workflow:mark_emails_bounced',
		"nti_pserve = nti.appserver.nti_pserve:main",
		"nti_runzeo = nti.monkey.nti_runzeo:main",
		"nti_multi-zodb-gc = nti.monkey.nti_multi_zodb_gc:main",
		"nti_multi-zodb-check-refs = nti.monkey.nti_multi_zodb_check_refs:main",
		"nti_zodbconvert = nti.monkey.nti_zodbconvert:main",
		"nti_qp = nti.mailer.queue:run_console",
		# XXX: NOTE: The following technique is NOT reliable and fails
		# under buildout or any other scenario that results in this package
		# not being the /last/ package installed.
		"pserve = nti.appserver.nti_pserve:main",  # This script overrides the one from pyramid d
		"runzeo = nti.monkey.nti_runzeo:main",	# This script overrides the one from ZEO
		"zodbconvert = nti.monkey.nti_zodbconvert:main",  # This script overrides the one from relstorage
	],
	"paste.app_factory": [
		"main = nti.appserver.standalone:configure_app",
		"gunicorn = nti.appserver.nti_gunicorn:dummy_app_factory"
	],
	"paste.filter_app_factory": [
		"cors = nti.wsgi.cors:cors_filter_factory", # BWC
		"cors_options = nti.wsgi.cors:cors_option_filter_factory", # BWC
		"ops_ping = nti.appserver.wsgi_ping:ping_handler_factory",
		"ops_identify = nti.app.authentication.wsgi_identifier:identify_handler_factory"
	],
	"paste.server_runner": [
		"http = nti.appserver.standalone:server_runner",
		"gunicorn = nti.appserver.nti_gunicorn:paste_server_runner"
	],
	"zodbupdate" : [  # Migrating class names through zodbupdate >= 0.5
		"chatserver_meetings = nti.chatserver.meeting:_bwc_renames"
	]
}

import platform
py_impl = getattr(platform, 'python_implementation', lambda: None)
IS_PYPY = py_impl() == 'PyPy'

TESTS_REQUIRE = [
	'WebTest', # 2.0 is incompatible in a minor way with 1.4. It also pulls in six, waitress, beautifulsoup4
	'blessings >= 1.5.1',  # A thin, practical wrapper around terminal coloring, styling, and positioning. Pulled in by nose-progressive(?)
	'coverage',	# Test coverage
	'fakeredis >= 0.4.1',
	'fudge',
	'ipdb >= 0.8',	# easier access to the ipython debugger from nose, --ipdb; however, messy with nose-progressive> consider pdbpp?
	'nose >= 1.3.0',
	'nose2[coverage_plugin]',
	'nose-timer',
	'nose-progressive >= 1.5',
	'nose-pudb >= 0.1.2',  # Nose integration: --pudb --pudb-failures. 0.1.2 requires trivial patch
	'pyhamcrest >= 1.8.0',
	'tempstorage >= 2.12.2',  # ZODB in-memory conflict-resolving storage; like MappingStorage, but handles changes
	'zope.testing >= 4.1.2',
	'zope.testrunner',
	'nti.nose_traceback_info',
	'nti.testing',
	'nti.app.testing',
]

setup(
	name='nti.dataserver',
	version='0.0',
	keywords='web pyramid pylons',
	author='NTI',
	author_email='jason.madden@nextthought.com',
	description='NextThought Dataserver',
	long_description='Dataserver README',
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers :: Education",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 2.7",
		"Framework :: Pylons :: ZODB :: Pyramid",
		"Internet :: WWW/HTTP",
		"Natural Language :: English",
		"Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
	],
	# Support unit tests of package
	tests_require=TESTS_REQUIRE,  # Needed for e.g., tox
	setup_requires=[
		# If we actually ran tests out of the box on a fresh install, we'd
		# need this:
		# 'nose >= 1.2.1',
		# But it's also listed in extras/test, and it's very hard to upgrade
		# when that changes
		# 'distribute >= 0.7.3', # Can't seem to include that anywhere
		# In theory this should make it possible to get
		# the svn revision number from svn 1.7. Doesn't seem
		# to work (with distribute?) at all. This causes
		# problems with buildout, so we need to disable tagging
		# in setup.cfg
		# 'setuptools_subversion >= 3.1'
	],
	install_requires=[
		'nti.common',
		'nti.containers',
		'nti.contentfragments',
		'nti.contentindexing',
		'nti.contenttypes.presentation',
		'nti.coremetadata',
		'nti.dataserver_core',
		'nti.dublincore',
		'nti.externalization',
		'nti.futures',
		'nti.geventwebsocket',
		'nti.links',
		'nti.metadata',
		'nti.mimetype',
		'nti.namedfile',
		'nti.ntiids',
		'nti.plasTeX',
		'nti.transactions',
		'nti.traversal',
		'nti.schema',
		'nti.site',
		'nti.utils',
		'nti.wref',
		'nti.zodb',
		'nti.zope_catalog',
		'objgraph',
		'pywikipedia',
		 # Zope Acquisition; used by contentratings implicitly
		 # cool concept. Pulls in ExtensionClass (which should only be used for acquisition)
		'Acquisition',
		'Chameleon', # (preferred) template rendering. pulled in by pyramid, but ensure latest version
		'ExtensionClass',
		'Mako',	 # fallback plain-text template render. pulled in by pyramid, but ensure latest version
		'Pillow',
		'RestrictedPython',
		'ZConfig',
		 # Depending on the final release, we may need to explicitly list each component.
		'ZODB3',
		'ZODB',
		'BTrees',
		'zdaemon',
		'persistent',
		'ZEO',
		# ZODB RelStorage:
		# 'pylibmc', # for memcached support (has third-party dep on memcache-devel)
		# 'MySQL-python', # mysql adapter--NOT needed, loaded from umysqldb
		# See also umysqldb for a mysql adapter that should be gevent compat, with same API
		# It depends on umysql, which has been released as 2.5 on pypi.
		# NOTE: This does not support unix socket connections
		# MySQL-python is mostly in C. umysql is entirely in C.
		# umysqldb uses (very small) parts of PyMySQL (which is entirely in python),
		# As of 2010-09-15, PyMySQL at github/petehunt is not being maintained,
		# but the original it was forked from, at github/lecram seems to be; both
		# have commits not in the released 0.5 that we need.
		# As of 2013-10-04 it looks like releases are being made to PyPI again,
		# and lecram is now maintaining the master copy at https://github.com/PyMySQL/PyMySQL/.
		# However, pymysql 0.6 is incompatible with relstorage. The cursors.Cursor
		# class changed from storing self.connection as weakref.proxy to a plain
		# weakref (requiring a call to dereference) which naturally breaks all users
		# of cursors:
		#	Module relstorage.storage:925 in f
		#	>>	return list(self._adapter.oidallocator.new_oids(cursor))
		#	Module relstorage.adapters.oidallocator:58 in new_oids
		#	>>	n = cursor.connection.insert_id()
		#	AttributeError: 'weakref' object has no attribute 'insert_id'
		# See https://github.com/PyMySQL/PyMySQL/issues/180.
		# This is fixed in 0.6.1, but umysqldb 1.0.3 already had a pin <0.6
		# MySQL-python (aka MySQLdb) has been renamed to moist but seems stalled (https://github.com/farcepest/moist)
		# On PyPy, we want pure PyMySQL, it's fastest.
		# Benchmarking, however, shows that MySQL-python is by far the fastest under CPython,
		# and MAY even be gevent friendly. It also seems like PyMySQL is also probably faster
		# than umysql under CPython, despite umysql's claims (have to finish confirming that).
		'umysql',
		'umysqldb == 1.0.4dev2' if not IS_PYPY else '', # requires PyMySQL < 0.6, but we want 0.6.1; hence our patch
		'RelStorage',
		'PyMySQL',
		'PyYAML',
		'python-memcached',	 # pure-python cache for relstorage. Must set cache-module-name. Needed for gevent
		 # See also http://pypi.python.org/pypi/neoppod/ for a completely different option
		'anyjson',
		 # 'appendonly >= 1.0.1', ZODB conflict-free structures featuring a Stack and more
		 # See also blist for a tree-structured list
		 # URL-safe "slugs" from arbitrary titles. Automatically
		 # deals with several non-ASCII scripts
		'awesome-slugify',
		'boto',	 # amazon
		'brownie',	 # Common utilities
		'cffi', # Foreign Function Interface, libffi required
		 # rating content objects (1.0-rc3 > 1.0 sadly, so specific)
		 # See also collective.subscribe for a different take, useful when we need
		 # this stuff globally (https://github.com/collective/collective.subscribe/tree/master/collective/subscribe)
		'contentratings',  # requires small patch to work without acquisition
		'cryptacular',	 # see z3c.crypt
		 # 'cryptography', # oauthlib
		'cssselect',  # Used by pyquery
		'cython',
		 # Adds support for detecting aborts to transactions which
		 # otherwise only detect failed commits
		'dm.transaction.aborthook',
		 # support for defining and evolving classes based on schemas
		 # pulls in dm.reuse
		'dm.zope.schema',
		'dolmen.builtins',	 # interfaces for common python types
		'filechunkio',	# Req'd for multi-put in boto == 2.5.2
		 # A very simple (one module, no deps) RSS and Atom feed generator.
		 # 1.7 is a modern rewrite with much better unicode and Py3k support
		'feedgenerator',
		'futures',
		'gevent' if not IS_PYPY else '', # We have a branch for this, installed in buildout.cfg
		'greenlet' if not IS_PYPY else '', # pypy has its own greenlet implementation
		'gunicorn',
		'hiredis' if not IS_PYPY else '', # Redis C parser (almost certainly an anti-optimization on PyPy)
		'isodate',	 # ISO8601 date/time/duration parser and formatter
		'itsdangerous', # Simple helper library for signing data that roundtrips through untrusted environments
		'logilab-common',
		'lxml', # Powerful and Pythonic HTML/XML processing library combining libxml2/libxslt with the ElementTree API. Also a pull parser.
		'nameparser', # Human name parsing
		'nltk',
		 # numpy is req'd by nltk, but not depended on. sigh.
		 # This turns out to be because it CANNOT be installed in a setup.py:
		 # Apparently it ships its own distutils. If you try to install from setup.py, you get
		 # Warning: distutils distribution has been initialized, it may be too late to add a subpackage command
		 # followed by compilation failures: fatal error 'Python.h' file not found. So you must
		 # install numpy manually with pip: pip install numpy
		 # or have it in requirements.txt (which we do).
		 # It also works to install it with buildout, which is the currently
		 # supported mechanism. This is how we do it with pypy too.
		'numpy' if not IS_PYPY else '',
		'paste',
		'perfmetrics',	# easy statsd metrics.
		'plone.i18n',	# provides ISO3166 country/codes and flag images
		'plone.scale',	 # image scaling/storage based on PIL
		'plone.namedfile',	 # much like zope.file, but some image-specific goodness.
		'premailer', # inline css for html emails
		'pyparsing', # used by rdflib
		 # Pure python PDF reading and manipulation library.
		'pyPDF2',
		'pyScss',
		 # See also z3c.rml for a complete PDF layout and rendering environment, which should
		 # work with page templates as well.
		 # jquery-like traversing of python datastructures. lxml, cssselect
		 # optional dependency on 'restkit' for interactive WSGI stuff (used to be Paste)
		'pyquery',
		'pyramid' ,
		'pyramid_chameleon',
		'pyramid_mako',
		'pyramid_mailer',  # Which uses repoze.sendmail
		'pyramid_who',
		'pyramid_zcml',
		'pyramid-openid',
		 # 'psycopg2 >= 2.5.1',	# PostGreSQL
		'pysaml2' if not IS_PYPY else '',
		 # Monitoring stats and instrumenting code
		'python-statsd',  # statsd client. statsd must be installed separately: https://github.com/etsy/statsd
		 # statsd server implementation, pure python. probably easier than setting up node. Might want to get it from https://github.com/sivy/py-statsd
		 # Consider also https://github.com/phensley/gstatsd
		'pystatsd',
		'pytz',
		 # Redis python client. Note that Amazon deployed servers are still in the 2.6 (2.4?) series
		'redis',
		'reportlab',
		 # There is a nice complete mock for it at fakeredis, installed for tests
		'repoze.catalog',
		'repoze.lru',  # LRU caching. Dep of Pyramid
		'repoze.sendmail',	# trunk has some good binary changes
		'repoze.who',  #
		'repoze.zodbconn',
		 # Requests: http for humans. Requests >= 1.0.x is depended on by httpie 0.4.
		 # We use just the generic part of the API and work back to 0.14.
		 # stripe also depends on just the minimal part of the api (their setup.py doesn't
		 # give a version) (?). grequests 0.1.0 is not compatible with this.
		 # If something used hooks, a change from 1.1 to 1.2 might break it; no initial issues seen
		'requests',
		'setproctitle',	 # used by gunicorn
		'setuptools',
		'simplejson',
		'six',
		'sympy',
		'supervisor',
		'transaction',
		 # See http://pypi.python.org/pypi/user-agents/ for a high-level
		 # library to do web user agent detection
		'webob',
		'whoosh',
		'z3c.appconfig',
		'z3c.autoinclude',
		'z3c.baseregistry',	 # ZCML configurable local component registries
		'z3c.batching',	 # result paging. Pulled in by z3c.table
		 # bcrypt/pbkdf2 for zope.password
		 # adds cryptacular and pbkdf2
		'z3c.bcrypt',
		 # PageTemplate access to macros through zope.component
		 # as opposed to traversal (which is good for us; Zope
		 # pulls *all* templates into memory/ZODB so they are traversable,
		 # but we haven't done that).
		'z3c.macro',
		'z3c.pagelet',
		'z3c.password',	# password policies
		'z3c.pt',  # Better ZPT support than plastex, add-in to Chameleon
		'z3c.ptcompat',	# Make zope.pagetemplate also use the Chameleon-based ZPT
		'z3c.rml',
		'z3c.schema',
		'z3c.table',	 # Flexible table rendering
		'zc.blist',	 # ZODB-friendly BTree-based list implementation. compare to plain 'blist'
		'zc.catalog',
		'zc.dict',	 # BTree based dicts that are subclassable
		'zc.displayname', # Simple pluggable display name support
		'zc.intid >= 2.0.0',
		'zc.lockfile',
		'zc.queue',
		'zc.zlibstorage',	# compressed records. Will be built-in to newer ZODB
		'zc.zodbdgc',
		'zodbpickle',
		'zope.app.broken',	 # Improved broken objects
		'zope.app.dependable', # simple dependency tracking; re-exported from zope.container
		'zope.applicationcontrol',	# Info about the app. currently unused
		'zope.annotation',
		'zope.authentication',
		'zope.broken',	 # This is actually deprecated, use the ZODB import
		'zope.browser',
		'zope.browserpage',
		'zope.browsermenu',	# Browser menu implementation for Zope.
		'zope.browserresource',
		'zope.catalog',
		'zope.cachedescriptors',
		'zope.component[persistentregistry]',
		 # Schema vocabularies based on querying ZCA; useful
		 # for views and other metadata. cf zope.vocabularyregistry
		'zope.componentvocabulary',
		'zope.configuration',
		 # zope.container 4.0.0a3 won't install in pypy; it has no python fallback
		 # for its proxying. A patch to its setup.py can make it install (see https://github.com/zopefoundation/zope.proxy/blob/master/setup.py), but it won't work
		 # reliably; nonetheless it is required because so many other things require zope.container:
		 # z3c.table, zope.catalog, zope.copypastemove, zope.file, zope.intid, zope.pluggableauth, zope.site
		 # If you do install it you can run this script again to get the missing deps.
		 # We have a branch of it that supports pypy
		'zope.container[zcml,zodb]',	# 4.0.0a3 or greater is required in the 4 series
		'zope.contentprovider',
		'zope.contenttype',	 # A utility module for content-type handling.
		'zope.copy',
		'zope.copypastemove[zcml]',  # zope.container dep
		'zope.datetime',
		'zope.deprecation',
		'zope.deferredimport',
		'zope.dottedname',
		'zope.dublincore',
		'zope.error',
		'zope.event',
		'zope.exceptions',
		'zope.filerepresentation',
		'zope.file',	 # zope.container dep
		'zope.formlib',	# Req'd by zope.mimetype among others,
		'zope.generations',
		'zope.hookable',  # explicitly list this to ensure we get the fast C version. Used by ZCA.
		'zope.i18n',
		'zope.i18nmessageid',
		'zope.index',
		'zope.interface',
		'zope.intid',
		'zope.keyreference',
		'zope.lifecycleevent',	# Object Added/Removed/etc events
		'zope.login',  # Providers of Zope3 authentication.ILoginPassword for Zope3 publisher interfaces; pulled in by zope.file[test] and indirectly zope.app.component[test]
		'zope.location',
		'zope.mimetype',
		'zope.minmax',
		'zope.pagetemplate',
		'zope.password',  # encrypted password management
		'zope.pluggableauth',# pluggable authentication for zope.auth; see also repoze.who; zope.container dependency
		 # Persistent, schema-based preferences with
		 # site- and local defaults
		'zope.preference',
		'zope.ptresource',
		'zope.publisher',
		'zope.principalannotation',	# Annotating principals in Zope3's global reg; pulled in indirectly by zope.app.component[test]
		'zope.principalregistry',   # Global principal registry component for Zope3
		'zope.processlifetime',
		'zope.proxy',	# 4.1.x support py3k, uses newer APIs. Not binary compat with older extensions, must rebuild. (In partic, req zope.security >= 3.9)
		'zope.server',	# DO NOT USED. Included as transitive for latest.
		'zope.sequencesort',  # advanced locale aware sorting
		'zope.schema',
		'zope.security[zcml,untrustedpython]',	 # >= 4.0.0b1 gets PyPy support!
		'zope.securitypolicy',
		'zope.session',	# 4.0.0a2 is out, should be fine
		'zope.site',	# local, persistent ZCA sites. zope.container dep
		'zope.size',
		 # parser and renderers for the classic Zope "structured text" markup dialect (STX).
		 # STX is a plain text markup in which document structure is signalled primarily by identation.
		 # Pulled in by ...?
		'zope.structuredtext',
		'zope.sqlalchemy', # needed by nti.badges, we have monkey patches
		'zope.tal',
		'zope.tales',
		'zope.traversing',
		 # Plug to make zope.schema's vocabulary registry ZCA
		 # based and thus actually useful
		'zope.vocabularyregistry',
		'zopyx.txng3.ext',
		 # Data analysis
		 # pandas,
		 # scikit-learn,
		 # rpy2, -- Requires R installed.
	],
	extras_require={
		'test': TESTS_REQUIRE,
		'tools': [
			 # WSGI middleware for profiling. Defaults to storing
			 # data in a sqlite file. Works across multiple gunicorn workers, does
			 # OK with websockets and greenlets.
			 # Depends on the system graphviz installation; an alternative is repoze.profile which has
			 # fewer dependencies, but less helpful output and doesn't work with multiple workers (?)
			 # Moved to buildout to reduce dep
			 # 'linesman >= 0.3.1',	 # less that 0.3.0 conflicts with pillow (wanted PIL)
			 # 'Pymacs >= 0.25', # checkout from git+https://github.com/pinard/Pymacs, run make. idiot thing uses a preprocessor, can't be directly installed
			 #'dblatex >= 0.3.4',  # content rendering, convert docbook to tex. disabled due to sandbox violation
			'epydoc >= 3.0.1',	# auto-api docs
			'httpie',
			'jsonschema',
			# A development tool to measure, monitor and analyze the memory behavior of Python objects.
			'pympler' if not IS_PYPY else '',
			'mistune',
			'ipython',	# the extra notebook is web based, pulls in tornado
			'logilab_astng >= 0.24.3',
			'pip',
			 #'pip-tools >= 0.3.4',	 # command pip-review, pip-dump -- replaced by bin/checkversions
			'pudb >= 2013.5.1', # Python full screen console debugger. Beats ipython's: import pudb; pdb.set_trace()
			'pylint',  # install astroid
			'pyramid_debugtoolbar >= 1.0.9',
			'readline >= 6.2.4.1' if not IS_PYPY else '', # built-in to pypy
			'repoze.sphinx.autointerface >= 0.7.1',
			'rope >= 0.9.4',  # refactoring library. c.f. ropemacs
			'ropemode >= 0.2',	# IDE helper for rope
			'jedi',
			'ropemacs',
			'snakefood', # dependency graphs
			'sphinx',	# Narrative docs
			'sphinxcontrib-programoutput >= 0.8',
			'sphinxtheme.readability >= 0.0.6',
			'virtualenv',
			'virtualenvwrapper',
			'zc.buildout >= 2.2.1',
			'z3c.dependencychecker >= 1.11',  # unused/used imports; see also tl.eggdeps
			 #'zodbbrowser >= 0.11.2', leads to version conflicts due to its old deps
			'zodbupdate >= 0.5',
			 # Monitoring stats and instrumenting code
			 # See above for python-statsd
			 # 'graphite-web >= 0.9.10', # web front end. Requires the /opt/graphite directory. Pulls in twisted.
			 # 'carbon >= 0.9.10', # storage daemon. Requires the /opt/graphite directory
			 # 'whisper >= 0.9.10', # database lib.
			 # See also https://github.com/hathawsh/graphite_buildout for a buildout to install node's statsd and graphite
			 # locally (you may need to use a different version of node)
			 # Managing translations
			'Babel >= 1.3',
			'lingua',
		]
	},
	dependency_links=[
		'git+https://github.com/NextThought/nti.plasTeX.git#egg=nti.plasTeX',
		'git+https://github.com/NextThought/nti.geventwebsocket.git#egg=nti.geventwebsocket',
		'git+https://github.com/NextThought/umysqldb.git#egg=umysqldb-1.0.4dev2'
	],
	zip_safe=False,
	package_dir={'': 'src'},
	packages=find_packages('src'),
	include_package_data=True,
	namespace_packages=['nti'],
	entry_points=entry_points,
	test_suite='nose2.compat.unittest.collector'
)
