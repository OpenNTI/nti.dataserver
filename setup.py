#!/usr/bin/env python

from setuptools import setup, find_packages

entry_points = {
	'console_scripts': [
		"nti_render = nti.contentrendering.nti_render:main",
		"nti_init_env = nti.dataserver.utils.nti_init_env:main",
		"nti_pubsub_device = nti.dataserver._PubSubDevice:main",
		"nti_init_shard = nti.dataserver.utils.nti_init_shard:main",
		"nti_cache_avatars = nti.dataserver.utils.nti_cache_avatars:main",
		"nti_create_user = nti.dataserver.utils.nti_create_user:main",
		"nti_create_class = nti.dataserver.utils.nti_create_class:main",
		"nti_create_friendslist = nti.dataserver.utils.nti_create_friendslist:main",
		"nti_add_remove_friends = nti.dataserver.utils.nti_add_remove_friends:main",
		"nti_enroll_class = nti.dataserver.utils.nti_enroll_class:main",
		"nti_join_community = nti.dataserver.utils.nti_join_community:main",
		"nti_set_generation = nti.dataserver.utils.nti_set_generation:main",
		"nti_set_password = nti.dataserver.utils.nti_set_password:main",
		"nti_follow_entity = nti.dataserver.utils.nti_follow_entity:main",
		"nti_remove_user = nti.dataserver.utils.nti_remove_user:main",
		"nti_update_object = nti.dataserver.utils.nti_update_object:main",
		"nti_export_entities = nti.dataserver.utils.nti_export_entities:main",
		"nti_set_user_attribute = nti.dataserver.utils.nti_set_user_attribute:main",
		"nti_delete_user_objects = nti.dataserver.utils.nti_delete_user_objects:main",
		"nti_export_user_objects = nti.dataserver.utils.nti_export_user_objects:main",
		"nti_sharing_listener = nti.appserver.application:sharing_listener_main",
		"nti_index_listener = nti.appserver.application:index_listener_main",
		"nti_reindex_entity_content = nti.contentsearch.utils.nti_reindex_entity_content:main",
		"nti_remove_user_indexed_content = nti.contentsearch.utils.nti_remove_user_indexed_content:main",
		"nti_remove_index_zombies = nti.contentsearch.utils.nti_remove_index_zombies:main",
		"nti_s3put = nti.contentlibrary.nti_s3put:main",
		"nti_gslopinionexport = nti.contentrendering.gslopinionexport:main",
		"nti_jsonpbuilder = nti.contentrendering.jsonpbuilder:main",
		"nti_default_root_sharing_setter = nti.contentrendering.default_root_sharing_setter:main",
		"nti_index_book_content = nti.contentrendering.indexer:main",
		'nti_bounced_email_batch = nti.appserver.bounced_email_workflow:process_sqs_messages',
		'nti_testing_mark_emails_bounced = nti.appserver.bounced_email_workflow:mark_emails_bounced',
		"pserve = nti.appserver.nti_pserve:main", # This script overrides the one from pyramid
	],
	"paste.app_factory": [
		"main = nti.appserver.standalone:configure_app",
		"gunicorn = nti.appserver.gunicorn:dummy_app_factory"
	],

	"paste.filter_app_factory": [
		"cors = nti.appserver.cors:cors_filter_factory",
		"cors_options = nti.appserver.cors:cors_option_filter_factory",
		"ops_ping = nti.appserver.wsgi_ping:ping_handler_factory"
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
#	tests_require = ['z3c.coverage','zope.testing'],
	setup_requires = [
		# If we actually ran tests out of the box on a fresh install, we'd
		# need this:
		#'nose >= 1.2.1',
		# But it's also listed in extras/test, and it's very hard to upgrade
		# when that changes
		#'distribute >= 0.6.32', # Can't seem to include that anywhere
		# In theory this should make it possible to get
		# the svn revision number from svn 1.7. Doesn't seem
		# to work (with distribute?)
		#'setuptools_subversion >= 3.0'
	],
	install_requires = [
		 # Zope Acquisition; used by contentratings implicitly
		 # cool concept. Pulls in ExtensionClass (which should not be used)
		'Acquisition >= 4.0a1',
		'Chameleon >= 2.11',
		 # 'friendly' fork of PIL, developed by Zope/Plone.
		 # PIL is currently (as of 2012-07) at version 1.1.7 (from 2009), which
		 # is the version that Pillow forked from in 2010 as version 1.0. So
		 # Pillow is currently way ahead of PIL
		'Pillow >= 1.7.8',
		'RestrictedPython >= 3.6.0',
		'ZConfig >= 2.9.3',
		 # NOTE: ZODB has a new release, 4.0.0a4 (Notice it's not ZODB3 anymore, so
		 # there's no need to hard-pin the ZODB3 version.) For this version, we
		 # will need to additionally include persistent >= 4.0.5 and BTrees >= 4.0.1, and ZEO >= 4.0.0
		 # which were pulled out of ZODB for better pypy support. We'll switch to it
		 # when it goes non-alpha. It may require a tweak to our monkey patch if
		 # has not been fixed.
		 # ZODB3 now has a 3.11.0a2 including a 4.x version of each above component.
		 # JAM is testing it, so don't hard pin this to 3.10.5; updates
		 # won't get picked up except on a new environment or manually. Depending on the final release,
		 # we may need to explicitly list each component.
		'ZODB3 >= 3.10.5',
		# ZODB RelStorage:
		# 'pylibmc', # for memcached support (has third-party dep on memcache-devel)
		# 'MySQL-python', # mysql adapter
		# See also umysqldb for a mysql adapter that should be gevent compat, with same API
		# It's currently being installed from requirements.txt because it has no release on pypi.
		# It depends on umysql, which has been released as 2.5 on pypi
		'umysql == 2.5',
		'RelStorage >= 1.5.1',
		'python-memcached >= 1.48', # pure-python cache for relstorage. Must set cache-module-name. Needed for gevent
		# See also http://pypi.python.org/pypi/neoppod/ for a completely different option

		'anyjson >= 0.3.3',
		'boto >= 2.6.0', # amazon
		'brownie >= 0.5.1', # Common utilities
		 # rating content objects (1.0-rc3 > 1.0 sadly, so specific)
		 # See also collective.subscribe for a different take, useful when we need
		 # this stuff globally (https://github.com/collective/collective.subscribe/tree/master/collective/subscribe)
		'contentratings == 1.0',
		'cryptacular >= 1.4.1', # see z3c.crypt
		'cssselect >= 0.7.1', # Used by pyquery
		'cython >= 0.17.3',
		# Adds support for detecting aborts to transactions which
		# otherwise only detect failed commits
		'dm.transaction.aborthook >= 1.0',
		# support for defining and evolving classes based on schemas
		# pulls in dm.reuse
		'dm.zope.schema >= 2.0.1',
		'dolmen.builtins >= 0.3.1', # interfaces for common python types
		'filechunkio >= 1.5', # Req'd for multi-put in boto == 2.5.2
		# A very simple (one module, no deps) RSS and Atom feed generator.
		# Possible downside: Last update Aug 2010
		'feedgenerator >= 1.2.1',
		'futures >= 2.1.3',
		#'gevent == 1.0rc1', Coming from requirements.txt right now
		# NOTE: gevent_zeromq and pyzmq are tightly coupled. Updating pyzmq
		# usually requires rebuilding gevent_zeromq. You'll get errors about 'Context has wrong size'.
		# You may be able to fix it with 'pip install -U --force --no-deps gevent_zeromq'. You may not;
		# if that doesn't work, the solution is to download gevent_zeromq manually, untar it, and
		# run 'python setup.py install'. It may be necessary to 'pip uninstall' this (and/or remove it from site-packages)
		# before running setup.py.
		# NOTE2: This will go away soon, merged into pyzmq 2.2dev as zmq.green
		'gevent_zeromq >= 0.2.5',
		'greenlet >= 0.4.0',
		'gunicorn == 0.17.0',
		'hiredis >= 0.1.1', # Redis C parser
		'html5lib == 0.95',
		 # WSGI middleware for profiling. Defaults to storing
		 # data in a sqlite file. Works across multiple gunicorn workers, does
		 # OK with websockets and greenlets. Needs trivial patch to work (display results) with
		 # webob 1.2, collects data ok without patch.
		 # Depends on the system graphviz installation; an alternative is repoze.profile which has
		 # fewer dependencies, but less helpful output and doesn't work with multiple workers (?)
		#'linesman >= 0.2.2', # Conflicts with Pillow. Modify requires.txt as part of the patch
		'logilab-common >= 0.58.3',
		'lxml >= 3.0.2', # Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API.
		'nameparser >= 0.2.3', # Human name parsing
		'nltk >= 2.0.4',
		# numpy is req'd by nltk, but not depended on. sigh.
		# This turns out to be because it CANNOT be installed in a setup.py:
		# Apparently it ships its own distutils. If you try to install from setup.py, you get
		# Warning: distutils distribution has been initialized, it may be too late to add a subpackage command
		# followed by compilation failures: fatal error 'Python.h' file not found. So you must
		# install numpy manually with pip: pip install numpy
		'numpy >= 1.6.2',
		'paste >= 1.7.5.1',
		'perfmetrics >= 1.0', # easy statsd metrics.
		'plone.scale >= 1.2.2', # image scaling/storage based on PIL
		'plone.namedfile >= 2.0', # much like zope.file, but some image-specific goodness.
		# Pure python PDF reading library. Not complex. Has newer fork pyPDF2, not yet on PyPI?:
		'pyPDF >= 1.13',
		# See also z3c.rml for a complete PDF layout and rendering environment, which should
		# work with page templates as well.
		# jquery-like traversing of python datastructures. lxml, cssselect
		# optional dependency on 'restkit' for interactive WSGI stuff (used to be Paste)
		'pyquery >= 1.2.4',
		'pyramid >= 1.4' ,
		'pyramid_tm >= 0.6',
		'pyramid_mailer >= 0.10', # Which uses repoze.sendmail
		'pyramid_who >= 0.3',
		'pyramid_zcml >= 0.9.2',
		'pyramid_zodbconn >= 0.4',
		'pyramid-openid >= 0.3.4',
		# Best if the system has ZMQ >= 2.2.0. Can work as far back as 2.1.7 (at least). 2.1.10 or better recommended;
		# I (JAM) *think* the ZMQ libs are all binary compatible so you can upgrade from 2.1 to 2.2
		# on the fly without touching the python level.
		# You may have to install this manually, depending on where zmq is installed.
		# something like:
		# pip install --install-option="--zmq=/opt/nti" pyzmq
		'pyzmq == 2.2.0', # TODO: 2.2.0.1 is out. It includes zmq.green and obsoletes gevent_zeromq. It is incompatible with having gevent_zeromq installed
		# Monitoring stats and instrumenting code
		'python-statsd >= 1.5.7', # statsd client. statsd must be installed separately: https://github.com/etsy/statsd
		 # statsd server implementation, pure python. probably easier than setting up node. Might want to get it from https://github.com/sivy/py-statsd
		 # Consider also https://github.com/phensley/gstatsd
		'pystatsd >= 0.1.6',
		'pytz >= 2012h',
		'rdflib >= 3.2.3',
		# Redis python client. Note that Amazon deployed servers are still in the 2.6 (2.4?) series
		'redis >= 2.7.2',
		# There is a nice complete mock for it at fakeredis, installed for tests
		'repoze.catalog >= 0.8.2',
		'repoze.lru >= 0.6', # LRU caching. Dep of Pyramid
		'repoze.sendmail >= 3.2',
		'repoze.who == 2.0', # 2.1b1 is out, should be drop in, may require changes
		'repoze.zodbconn >= 0.14',
		'grequests >= 0.1.0', #replaces requests.async in 0.13
		'requests >= 0.14.2,<1.0', # HTTP. NOTE: 1.0.x is out, but not full backwards compat. Since some tools (httpie) depend on it, wait until they are ready
		'scss >= 0.8.72',
		'setproctitle >= 1.1.6',
		'setuptools >= 0.6c11',
		'simplejson >= 2.6.2',
		'sympy == 0.7.2', # sympy-docs-html-0.7.1 is currently greater
		'six >= 1.2.0',
		#'slimit',
		'supervisor >= 3.0b1',
		'transaction >= 1.3.0, < 1.4', # 1.4.0b1 is out. It looks good but will require a code review for its 'attempts' updates, exception changes, and compat with dm.transaction
		'webob >= 1.2.3',
		'whoosh >= 2.4.1',
		'z3c.baseregistry >= 2.0.0', # ZCML configurable local component registries
		'z3c.batching >= 1.1.0', # result paging. Pulled in by z3c.table
		 # bcrypt/pbkdf2 for zope.password
		 # adds cryptacular and pbkdf2
		'z3c.bcrypt >= 1.1',
		#'z3c.coverage >= 1.3.0', # TODO: Do we need this?
		'z3c.password >= 0.11.1', # password policies
		'z3c.pt >= 2.2.3', # Better ZPT support than plastex, add-in to Chameleon
		# TODO: z3c.ptcompat? We already have zope.pagetemplate listed
		'z3c.table >= 1.0.0', # Flexible table rendering
		'zc.dict >= 1.3b1', # BTree based dicts that are subclassable
		'zc.intid >= 1.0.1',
		'zc.lockfile >= 1.0.2',
		'zc.queue >= 1.3',
		'zc.zlibstorage >= 0.1.1', # compressed records. Will be built-in to newer ZODB
		'zc.zodbdgc >= 0.6.1',
		#'zetalibrary',
		'zodburi >= 1.1', # used by pyramid_zodbconn
		'zope.app.broken >= 3.6.0', # Improved broken objects
		'zope.app.component >= 3.9.3', # bwc only, DO NOT IMPORT. pulled in by contentratings
		'zope.app.interface >= 3.6.0', # bwc only, DO NOT IMPORT. pulled in by contentratings
		'zope.annotation >= 3.5.0',
		'zope.broken >= 3.6.0', # This is actually deprecated, use the ZODB import
		'zope.browser >= 1.3',
		'zope.browserpage >= 4.0.0',
		'zope.browserresource >= 3.12.0',
		'zope.catalog >= 3.8.2',
		'zope.cachedescriptors >= 3.5.1',
		'zope.component >= 4.0.1',
		# Schema vocabularies based on querying ZCA; useful
		# for views and other metadata
		'zope.componentvocabulary >= 1.0.1',
		'zope.configuration >= 4.0.1',
		'zope.container >= 3.12.0',
		'zope.contenttype >= 3.5.5', # A utility module for content-type handling.
		'zope.copy >= 4.0.0',
		'zope.datetime >= 3.4.1',
		'zope.deprecation >= 4.0.1',
		'zope.deferredimport >= 3.5.3', # useful with zope.deprecation. Req'd by contentratings
		'zope.dottedname >= 3.4.6',
		'zope.dublincore >= 3.8.2',
		'zope.error >= 4.0.0',
		'zope.event >= 4.0.1',
		'zope.exceptions >= 4.0.4',
		'zope.filerepresentation >= 3.6.1',
		'zope.file >= 0.6.2',
		'zope.formlib >= 4.2.0', # Req'd by zope.mimetype among others,
		'zope.generations >= 3.7.1',
		'zope.hookable >= 4.0.1', # explicitly list this to ensure we get the fast C version. Used by ZCA.
		'zope.i18n >= 3.8.0',
		'zope.i18nmessageid >= 4.0.1',
		'zope.index >= 3.6.4',
		'zope.interface >= 4.0.2',
		'zope.intid >= 3.7.2',
		'zope.lifecycleevent >= 3.7.0',
		'zope.location >= 4.0.0',
		'zope.mimetype >= 1.3.1',
		'zope.minmax >= 1.1.2',
		'zope.pagetemplate >= 4.0.0',
		'zope.password >= 3.6.1', # encrypted password management
		'zope.publisher >= 3.13.1',
		'zope.processlifetime >= 1.0',
		'zope.proxy >= 4.1.0', # 4.1.x support py3k, uses newer APIs. Not binary compat with older extensions, must rebuild. (In partic, req zope.security >= 3.9)
		'zope.schema >= 4.2.2',
		'zope.security >= 3.9.0', # 3.9.0 and zope.proxy 4.1.0 go together
		'zope.site >= 3.9.2', # local, persistent ZCA sites
		'zope.size >= 3.5.0',
		'zope.tal >= 3.6.1',
		'zope.tales >= 3.5.3',
		'zope.traversing >= 3.14.0',
		# textindexng3
		'zopyx.txng3.core >= 3.6.1.1',
		'zopyx.txng3.ext >= 3.3.3',
        # Data analysis
        # pandas,
        # scikit-learn,
        # rpy2, -- Requires R installed.
		],
	extras_require = {
		'test': [
			'coverage >= 3.6b1', # Test coverage
			'nose >= 1.2.1',
			'zope.testing >= 4.1.1',
			'zc.buildout == 1.6.3',
			'nose-progressive',
			'pyhamcrest >= 1.6',
			'WebTest >= 1.4.3',
			'fakeredis >= 0.3.0',
			'tempstorage >= 2.12.2', # ZODB in-memory conflict-resolving storage; like MappingStorage, but handles changes
			'fudge'],
		'tools': [
			'pyramid_debugtoolbar >= 1.0.3',
			'dblatex >= 0.3.4', # content rendering, convert docbook to tex
			'ipython[notebook] >= 0.13.1', # notebook is web based, pulls in tornado
			'pudb', # Python full screen console debugger. Beats ipython's: import pudb; pdb.set_trace()
			'nose-pudb >= 0.1.2', # Nose integration: --pudb --pudb-failures. 0.1.2 requires trivial patch
			'readline >= 6.2.4.1',
			'httpie == 0.3.1', # 0.3.1 explicitly requires requests < 1.0
			'logilab_astng >= 0.24.1',
			'pip-tools >= 0.2.1', # command pip-review, pip-dump
			'pylint >= 0.26.0',
			'zodbupdate >= 0.5',
			'zodbbrowser >= 0.10.4',
			'sphinx >= 1.1.3', # Narrative docs
			'sphinxtheme.readability >= 0.0.6',
			'repoze.sphinx.autointerface >= 0.7.1',
			'sphinxcontrib-programoutput >= 0.8',
			'epydoc >= 3.0.1', # auto-api docs
			'rope >= 0.9.4', # refactoring library. c.f. ropemacs
			'ropemode >= 0.2', # IDE helper for rope
			#'Pymacs >= 0.25',
			'virtualenv >= 1.8.4',
			'pip >= 1.2.1',
			# Monitoring stats and instrumenting code
			# See above for python-statsd
			#'graphite-web >= 0.9.10', # web front end. Requires the /opt/graphite directory. Pulls in twisted.
			#'carbon >= 0.9.10', # storage daemon. Requires the /opt/graphite directory
			'whisper >= 0.9.10', # database lib.
			# Managing translations
			'Babel >= 0.9.6',
			'lingua >= 1.3',
			]
	},
	message_extractors = { '.': [
		('**.py',   'lingua_python', None ),
		('**.pt',   'lingua_xml', None ),
		]},
	dependency_links = ['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
	packages = find_packages('src'),
	package_dir = {'': 'src'},
	include_package_data = True,
	namespace_packages=['nti',],
	zip_safe = False,
	entry_points = entry_points
	)
