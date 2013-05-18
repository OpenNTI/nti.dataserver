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
		"nti_index_book_content = nti.contentrendering.book_content_indexer:main",
		"nti_index_book_video_transcripts = nti.contentrendering.video_transcript_indexer:main",
		'nti_bounced_email_batch = nti.appserver.bounced_email_workflow:process_sqs_messages',
		'nti_testing_mark_emails_bounced = nti.appserver.bounced_email_workflow:mark_emails_bounced',
		"pserve = nti.appserver.nti_pserve:main",  # This script overrides the one from pyramid
		"runzeo = nti.monkey.nti_runzeo:main",  # This script overrides the one from ZEO
		"zodbconvert = nti.monkey.nti_zodbconvert:main",  # This script overrides the one from relstorage
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
		"http = nti.appserver.standalone:server_runner",
		"gunicorn = nti.appserver.gunicorn:paste_server_runner"
	],
	"nose.plugins.0.10" : [
		"zopeexceptionlogpatch = nti.tests:ZopeExceptionLogPatch"
	],
	"zodbupdate" : [  # Migrating class names through zodbupdate >= 0.5
		"chatserver_meetings = nti.chatserver.meeting:_bwc_renames"
	]
}

import platform
py_impl = getattr(platform, 'python_implementation', lambda: None)
IS_PYPY = py_impl() == 'PyPy'

try:
	import zope.container
except ImportError:
	HAVE_ZCONT = False
else:
	HAVE_ZCONT = True

TESTS_REQUIRE = [
	'WebTest >= 2.0.5',  # 2.0 is incompatible in a minor way with 1.4. It also pulls in six, waitress, beautifulsoup4
	'blessings >= 1.5',  # A thin, practical wrapper around terminal coloring, styling, and positioning. Pulled in by nose-progressive(?)
	'coverage >= 3.6',  # Test coverage
	'fakeredis >= 0.3.1',
	'fudge',
	'ipdb >= 0.7',  # easier access to the ipython debugger from nose, --ipdb; however, messy with nose-progressive> consider pdbpp?
	'nose >= 1.3.0',
	'nose-timer >= 0.1.2',
	'nose-progressive >= 1.5',
	'nose-pudb >= 0.1.2',  # Nose integration: --pudb --pudb-failures. 0.1.2 requires trivial patch
	'pyhamcrest >= 1.7.1',
	'tempstorage >= 2.12.2',  # ZODB in-memory conflict-resolving storage; like MappingStorage, but handles changes
	# 'z3c.coverage >= 2.0.0', # For HTML coverage reports that are prettier than plain 'coverage' TODO: Do we need this?
	'zope.testing >= 4.1.2',
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
		# 'distribute >= 0.6.40', # Can't seem to include that anywhere
		# In theory this should make it possible to get
		# the svn revision number from svn 1.7. Doesn't seem
		# to work (with distribute?)
		# 'setuptools_subversion >= 3.0'
	],
	install_requires=[
		# Zope Acquisition; used by contentratings implicitly
		# cool concept. Pulls in ExtensionClass (which should only be used for acquisition)
		'Acquisition >= 4.0' if not IS_PYPY else '',  # Extensions don't build on pypy
		'Chameleon >= 2.11',  # (preferred) template rendering. pulled in by pyramid, but ensure latest version
		'ExtensionClass >= 4.1a1',
		'Mako >= 0.8.0',  # fallback plain-text template render. pulled in by pyramid, but ensure latest version
		# 'friendly' fork of PIL, developed by Zope/Plone.
		# PIL is currently (as of 2012-07) at version 1.1.7 (from 2009), which
		# is the version that Pillow forked from in 2010 as version 1.0. So
		# Pillow is currently way ahead of PIL. Pillow 2 is Python 3 compatible (and partly pypy)
		# includes transparent png support, and is much cleaned up, otherwise api compatible with pillow 1/PIL 1
		'Pillow >= 2.0.0',
		'RestrictedPython >= 3.6.0',
		'ZConfig >= 3.0.3',  # 3.0.3 reqd for pypy/python3 support. requires zodb3 3.11.0a3+
		 # NOTE: ZODB has a new release, 4.0.0b2 (Notice it's not ZODB3 anymore, so
		 # there's no need to hard-pin the ZODB3 version.) For this version, we
		 # will need to additionally include persistent >= 4.0.6 and BTrees >= 4.0.5, and ZEO >= 4.0.0, and zdaemon
		 # which were pulled out of ZODB for better pypy and py3 support; ZODB3 is now a meta
		 # release, which is falling behind the real versions.
		 # It may require a tweak to our monkey patch if has not been fixed;
		 # see https://github.com/zopefoundation/ZEO/pull/1
		 # (Said patch is merged, but not yet released)
		 # ZODB3 now has a 3.11.0a3 including a 4.x version of each above component.
		 # This has been in testing for many months and is stable. It is needed
		 # (even though alpha at the moment) to work with other updated deps.
		 # Depending on the final release, we may need to explicitly list each component.
		'ZODB3 >= 3.11.0a3', # Unfortunately, pulled in by zopyx.txng3.core, so do make sure we get the latest
		'ZODB >= 4.0.0b2',
		'BTrees >= 4.0.6',
		'zdaemon >= 4.0.0',
		'persistent >= 4.0.6',
		'ZEO >= 4.0.0a1',
		# ZODB RelStorage:
		# 'pylibmc', # for memcached support (has third-party dep on memcache-devel)
		# 'MySQL-python', # mysql adapter--NOT needed, loaded from umysqldb
		# See also umysqldb for a mysql adapter that should be gevent compat, with same API
		# It depends on umysql, which has been released as 2.5 on pypi. NOTE: This does not support unix socket connections
		'umysql == 2.5',
		'umysqldb >= 1.0.2',
		'RelStorage >= 1.5.1',
		'python-memcached >= 1.51',  # pure-python cache for relstorage. Must set cache-module-name. Needed for gevent
		# See also http://pypi.python.org/pypi/neoppod/ for a completely different option
		'anyjson >= 0.3.3',
		# 'appendonly >= 1.0.1', ZODB conflict-free structures featuring a Stack and more
		# See also blist for a tree-structured list
		'boto >= 2.9.3',  # amazon
		'brownie >= 0.5.1',  # Common utilities
		 # rating content objects (1.0-rc3 > 1.0 sadly, so specific)
		 # See also collective.subscribe for a different take, useful when we need
		 # this stuff globally (https://github.com/collective/collective.subscribe/tree/master/collective/subscribe)
		'contentratings == 1.0',  # requires small patch to work without acquisition
		'cryptacular >= 1.4.1',  # see z3c.crypt
		'cssselect == 0.7.1',  # Used by pyquery (0.8 not compatible with pyquery 1.2.4, :first raises AttributeError)
		'cython >= 0.19.1',
		# Adds support for detecting aborts to transactions which
		# otherwise only detect failed commits
		'dm.transaction.aborthook >= 1.0',
		# support for defining and evolving classes based on schemas
		# pulls in dm.reuse
		'dm.zope.schema >= 2.0.1',
		'dolmen.builtins >= 0.3.1',  # interfaces for common python types
		'filechunkio >= 1.5',  # Req'd for multi-put in boto == 2.5.2
		# A very simple (one module, no deps) RSS and Atom feed generator.
		# 1.5 is a modern rewrite with much better unicode and Py3k support
		'feedgenerator == 1.5',
		'futures >= 2.1.3',
		# 'gevent == 1.0rc1', Coming from requirements.txt right now
		'greenlet >= 0.4.0',
		'gunicorn >= 0.17.4',
		'hiredis >= 0.1.1',  # Redis C parser
		# HTML5 parsing library
		# JAM: 1.0b1 is out, but demonstrates some strange behaviour. When
		# indexing a book, each XHTML file is converted to plain
		# text using nti.contentfragments, which in turn uses html5lib
		# to parse. In the Prealgebra book, when we get to the Inequalities
		# section (~40 files in), the file is suddenly misparsed, with random <c> element tokens
		# being created, having attributes of the text content: <c warren buffett 100-million-dollars>
		# xmllint reports the file to be well-formed (though not actually valid XHTML),
		# and it is always this file.
		# it almost looks like something is messing up all the regexes it uses? Or
		# maybe we are not closing something right? There doesn't seem to be any
		# parallelism involved. This is under python 2.7.3
		'html5lib == 0.95',
		'isodate >= 0.4.9',  # ISO8601 date/time/duration parser and formatter
		'logilab-common >= 0.59.1',
		'lxml >= 3.2.1',  # Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API.
		'nameparser >= 0.2.7',  # Human name parsing
		'nltk >= 2.0.4',
		# numpy is req'd by nltk, but not depended on. sigh.
		# This turns out to be because it CANNOT be installed in a setup.py:
		# Apparently it ships its own distutils. If you try to install from setup.py, you get
		# Warning: distutils distribution has been initialized, it may be too late to add a subpackage command
		# followed by compilation failures: fatal error 'Python.h' file not found. So you must
		# install numpy manually with pip: pip install numpy
		# or have it in requirements.txt (which we do)
		'numpy' if not IS_PYPY else '',
		'paste >= 1.7.5.1',
		'perfmetrics >= 1.0',  # easy statsd metrics.
		'plone.i18n >= 2.0.6', # provides ISO3166 country/codes and flag images
		'plone.scale >= 1.3.1',  # image scaling/storage based on PIL
		'plone.namedfile >= 2.0.1',  # much like zope.file, but some image-specific goodness.
		'pyparsing >= 1.5.6, < 2.0.0',  # used by matplotlib, experimental in zopyx.txng.core
		# Pure python PDF reading library. Not complex. Has newer fork pyPDF2, not yet on PyPI?
		'pyPDF >= 1.13',
		# See also z3c.rml for a complete PDF layout and rendering environment, which should
		# work with page templates as well.
		# jquery-like traversing of python datastructures. lxml, cssselect
		# optional dependency on 'restkit' for interactive WSGI stuff (used to be Paste)
		'pyquery >= 1.2.4',
		'pyramid >= 1.4.1' ,
		'pyramid_mailer >= 0.11',  # Which uses repoze.sendmail
		'pyramid_who >= 0.3',
		'pyramid_zcml >= 1.0.0',
		'pyramid_zodbconn >= 0.4',
		'pyramid-openid >= 0.3.4',
		# Monitoring stats and instrumenting code
		'python-statsd >= 1.6.0',  # statsd client. statsd must be installed separately: https://github.com/etsy/statsd
		 # statsd server implementation, pure python. probably easier than setting up node. Might want to get it from https://github.com/sivy/py-statsd
		 # Consider also https://github.com/phensley/gstatsd
		'pystatsd >= 0.1.6',
		'pytz >= 2013b',
		# RDF and embedded RDFa parsing.
		# NOTE: 4.0.0 is out, but its URI validation is too strict and fails
		# in the realworld, so the recomendation is to use 3.4.0.
		# See https://groups.google.com/forum/#!msg/rdflib-dev/Hic23YlBs6Y/PUwYzD2jcX4J
		'rdflib == 3.4.0',
		# Redis python client. Note that Amazon deployed servers are still in the 2.6 (2.4?) series
		'redis >= 2.7.5',
		# There is a nice complete mock for it at fakeredis, installed for tests
		'repoze.catalog >= 0.8.2',
		'repoze.lru >= 0.6',  # LRU caching. Dep of Pyramid
		'repoze.sendmail >= 4.0',  # trunk has some good binary changes
		'repoze.who >= 2.1',  #
		'repoze.zodbconn >= 0.14',
		 # Requests: http for humans. Requests >= 1.0.x is depended on by httpie 0.4.
		 # We use just the generic part of the API and work back to 0.14.
		 # stripe also depends on just the minimal part of the api (their setup.py doesn't
		 # give a version) (?). grequests 0.1.0 is not compatible with this.
		 # If something used hooks, a change from 1.1 to 1.2 might break it; no initial issues seen
		'requests >= 1.2.0',
		# 'scss >= 0.8.72', # we no longer use
		'setproctitle >= 1.1.7',  # used by gunicorn
		'setuptools >= 0.6c11',
		'simplejson >= 3.3.0',
		'six >= 1.3.0',
		'sympy == 0.7.2',  # sympy-docs-html-0.7.1 is currently greater
		'stripe >= 1.9.1',  # stripe payments
		# 'slimit',
		'supervisor >= 3.0b1',
		'transaction >= 1.4.1',
		# See http://pypi.python.org/pypi/user-agents/ for a high-level
		# library to do web user agent detection
		'WebError >= 0.10.3',  # Error-handling middleware, extracted from Paste (yet turns out to still be dependent on paste. sigh)
		'webob >= 1.2.3',
		'whoosh >= 2.4.1',
		'z3c.baseregistry >= 2.0.0',  # ZCML configurable local component registries
		'z3c.batching >= 2.0.0',  # result paging. Pulled in by z3c.table
		 # bcrypt/pbkdf2 for zope.password
		 # adds cryptacular and pbkdf2
		'z3c.bcrypt >= 1.1',
		'z3c.password >= 1.0.0a1',  # password policies
		'z3c.pt >= 3.0.0a1',  # Better ZPT support than plastex, add-in to Chameleon
		'z3c.ptcompat >= 2.0.0a1',  # Make zope.pagetemplate also use the Chameleon-based ZPT
		'z3c.table >= 2.0.0a1',  # Flexible table rendering
		'zc.blist >= 1.0b2',  # ZODB-friendly BTree-based list implementation. compare to plain 'blist'
		'zc.dict >= 1.3b1',  # BTree based dicts that are subclassable
		'zc.intid >= 1.0.1',
		'zc.lockfile >= 1.1.0',
		'zc.queue >= 2.0.0a1',
		'zc.zlibstorage >= 0.1.1',  # compressed records. Will be built-in to newer ZODB
		'zc.zodbdgc >= 0.6.1',
		# 'zetalibrary',
		'zodburi >= 2.0b1',  # used by pyramid_zodbconn
		'zope.app.broken >= 3.6.0',  # Improved broken objects
		'zope.app.component >= 3.9.3',  # bwc only, DO NOT IMPORT. pulled in by contentratings
		'zope.app.interface >= 3.6.0',  # bwc only, DO NOT IMPORT. pulled in by contentratings
		'zope.applicationcontrol >= 4.0.0a1',  # Info about the app. currently unused
		'zope.annotation >= 4.2.0',
		'zope.authentication >= 4.1.0',
		'zope.broken >= 3.6.0',  # This is actually deprecated, use the ZODB import
		'zope.browser >= 2.0.2',
		'zope.browserpage >= 4.1.0a1',
		'zope.browsermenu >= 4.1.0a1',  # Browser menu implementation for Zope.
		'zope.browserresource >= 4.0.1',
		'zope.catalog >= 4.0.0a1' if HAVE_ZCONT else '',  # zope.container dependency
		'zope.cachedescriptors >= 4.0.0',
		'zope.component[persistentregistry] >= 4.1.0',
		# Schema vocabularies based on querying ZCA; useful
		# for views and other metadata. cf zope.vocabularyregistry
		'zope.componentvocabulary >= 2.0.0a1',
		'zope.configuration >= 4.0.2',
		# zope.container 4.0.0a3 won't install in pypy; it has no python fallback
		# for its proxying. A patch to its setup.py can make it install (see https://github.com/zopefoundation/zope.proxy/blob/master/setup.py), but it won't work
		# reliably; nonetheless it is required because so many other things require zope.container:
		# z3c.table, zope.catalog, zope.copypastemove, zope.file, zope.intid, zope.pluggableauth, zope.site
		# If you do install it you can run this script again to get the missing deps
		'zope.container[zcml,zodb] >= 4.0.0a3' if not IS_PYPY else '',  # 4.0.0a3 or greater is required in the 4 series
		'zope.contentprovider >= 4.0.0a1',
		'zope.contenttype >= 4.0.1',  # A utility module for content-type handling.
		'zope.copy >= 4.0.2',
		'zope.copypastemove[zcml] >= 4.0.0a1' if HAVE_ZCONT else '',  # zope.container dep
		'zope.datetime >= 4.0.0',
		'zope.deprecation >= 4.0.2',
		'zope.deferredimport >= 4.0.0',  # useful with zope.deprecation. Req'd by contentratings
		'zope.dottedname >= 4.0.1',
		'zope.dublincore >= 4.0.0',
		'zope.error >= 4.1.0',
		'zope.event >= 4.0.2',
		'zope.exceptions >= 4.0.6',
		'zope.filerepresentation >= 4.0.2',
		'zope.file >= 0.6.2' if HAVE_ZCONT else '',  # zope.container dep
		'zope.formlib >= 4.3.0a1',  # Req'd by zope.mimetype among others,
		'zope.generations >= 4.0.0a1',
		'zope.hookable >= 4.0.1',  # explicitly list this to ensure we get the fast C version. Used by ZCA.
		'zope.i18n >= 4.0.0a4',
		'zope.i18nmessageid >= 4.0.2',
		'zope.index >= 4.0.1',
		'zope.interface >= 4.0.5',
		'zope.intid >= 4.0.0a1' if HAVE_ZCONT else '',
		'zope.keyreference >= 4.0.0a2',
		'zope.lifecycleevent >= 4.0.2',  # Object Added/Removed/etc events
		'zope.login >= 2.0.0a1',  # Providers of Zope3 authentication.ILoginPassword for Zope3 publisher interfaces; pulled in by zope.file[test] and indirectly zope.app.component[test]
		'zope.location >= 4.0.2',
		'zope.mimetype == 1.3.1',  # freeze on 1.3.1 pending 2.0.0a2, https://github.com/zopefoundation/zope.mimetype/pull/1
		'zope.minmax >= 2.0.0',
		'zope.pagetemplate >= 4.0.4',
		'zope.password >= 4.0.2',  # encrypted password management
		'zope.pluggableauth >= 2.0.0a1' if HAVE_ZCONT else '',  # pluggable authentication for zope.auth; see also repoze.who; zope.container dependency
		'zope.ptresource >= 4.0.0a1',
		'zope.publisher >= 4.0.0a4',
		'zope.principalannotation >= 4.0.0a1',  # Annotating principals in Zope3's global reg; pulled in indirectly by zope.app.component[test]
		'zope.principalregistry >= 4.0.0a2',  # Global principal registry component for Zope3
		'zope.processlifetime >= 2.0.0',
		'zope.proxy >= 4.1.3',  # 4.1.x support py3k, uses newer APIs. Not binary compat with older extensions, must rebuild. (In partic, req zope.security >= 3.9)
		'zope.server >= 3.9.0',  # DO NOT USED. Included as transitive for latest.
		'zope.sequencesort >= 4.0.1',  # advanced locale aware sorting
		'zope.schema >= 4.3.2',
		'zope.security[zcml,untrustedpython] >= 4.0.0b1',  # >= 4.0.0b1 gets PyPy support!
		'zope.securitypolicy >= 4.0.0a1',
		'zope.session >= 4.0.0a1',  # 4.0.0a1 is out, should be fine
		'zope.site >= 4.0.0a1' if HAVE_ZCONT else '',  # local, persistent ZCA sites. zope.container dep
		'zope.size >= 4.0.1',
		# parser and renderers for the classic Zope "structured text" markup dialect (STX).
		# STX is a plain text markup in which document structure is signalled primarily by identation.
		# Pulled in by ...?
		'zope.structuredtext >= 4.0.0',
		'zope.tal >= 4.0.0a1',
		'zope.tales >= 4.0.1',
		'zope.traversing >= 4.0.0a3',
		# Plug to make zope.schema's vocabulary registry ZCA
		# based and thus actually useful
		'zope.vocabularyregistry >= 1.0.0',
		# textindexng3
		'zopyx.txng3.core >= 3.6.1.1' if not IS_PYPY else '',  # extensions don't build
		'zopyx.txng3.ext >= 3.3.4' if not IS_PYPY else '',
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
		 	'linesman >= 0.3.1',  # less that 0.3.0 conflicts with pillow (wanted PIL)
			# 'Pymacs >= 0.25', # checkout from git+https://github.com/pinard/Pymacs, run make. idiot thing uses a preprocessor, can't be directly installed
			'dblatex >= 0.3.4',  # content rendering, convert docbook to tex
			'epydoc >= 3.0.1',  # auto-api docs
			'httpie >= 0.5.1',  # 0.4.0 explicitly requires requests > 1.0.4, 0.3.1 explicitly requires requests < 1.0
			'ipython >= 0.13.2',  # the extra notebook is web based, pulls in tornado
			'logilab_astng >= 0.24.3',
			'pip >= 1.3.1',
			'pip-tools >= 0.3.1',  # command pip-review, pip-dump
			'pudb >= 2013.1',  # Python full screen console debugger. Beats ipython's: import pudb; pdb.set_trace()
			'pylint >= 0.28.0' if not IS_PYPY else '',
			'pyramid_debugtoolbar >= 1.0.6',
			'readline >= 6.2.4.1' if not IS_PYPY else '',
			'repoze.sphinx.autointerface >= 0.7.1',
			'rope >= 0.9.4',  # refactoring library. c.f. ropemacs
			'ropemode >= 0.2',  # IDE helper for rope
			'sphinx >= 1.2b1',  # Narrative docs
			'sphinxcontrib-programoutput >= 0.8',
			'sphinxtheme.readability >= 0.0.6',
			'virtualenv >= 1.9.1',
			'virtualenvwrapper >= 4.0',
			'zc.buildout >= 2.1.0',
			'z3c.dependencychecker >= 1.11',  # unused/used imports; see also tl.eggdeps
			'zodbbrowser >= 0.10.4',
			'zodbupdate >= 0.5',
			# Monitoring stats and instrumenting code
			# See above for python-statsd
			# 'graphite-web >= 0.9.10', # web front end. Requires the /opt/graphite directory. Pulls in twisted.
			# 'carbon >= 0.9.10', # storage daemon. Requires the /opt/graphite directory
			# 'whisper >= 0.9.10', # database lib.
			# See also https://github.com/hathawsh/graphite_buildout for a buildout to install node's statsd and graphite
			# locally (you may need to use a different version of node)
			# Managing translations
			'Babel >= 0.9.6',
			'lingua >= 1.5',
			]
	},
	message_extractors={ 'src': [
		('**.py', 'lingua_python', None),
		('**.pt', 'lingua_xml', None),
		('**.zcml', 'lingua_zcml', None),
		]},
	dependency_links=['http://svn.wikimedia.org/svnroot/pywikipedia/trunk/pywikipedia/'],
	packages=find_packages('src'),
	package_dir={'': 'src'},
	include_package_data=True,
	namespace_packages=['nti', ],
	zip_safe=False,
	entry_points=entry_points
	)
