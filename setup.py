import codecs
from setuptools import setup, find_packages

entry_points = {
    'console_scripts': [
        # dataserver
        "nti_shards = nti.dataserver.utils.nti_shards:main",
        "nti_init_env = nti.dataserver.utils.nti_init_env:main",
        "nti_interactive = nti.dataserver.utils.nti_interactive:main",
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
        # NOTE: The command line tools are deprecated. Leave the setup.py entry points
        # pointing to this package to get the deprecation notice
        'nti_bounced_email_batch = nti.appserver.bounced_email_workflow:process_sqs_messages',
        'nti_testing_mark_emails_bounced = nti.appserver.bounced_email_workflow:mark_emails_bounced',
        "nti_pserve = nti.appserver.nti_pserve:main",
        # XXX: NOTE: The following technique is NOT reliable and fails
        # under buildout or any other scenario that results in this package
        # not being the /last/ package installed.
        # This script overrides the one from pyramid d
        "pserve = nti.appserver.nti_pserve:main",
    ],
    "paste.app_factory": [
        "main = nti.appserver.standalone:configure_app",
        "gunicorn = nti.appserver.nti_gunicorn:dummy_app_factory"
    ],
    "paste.filter_app_factory": [
        "cors = nti.wsgi.cors:cors_filter_factory",  # BWC
        "cors_options = nti.wsgi.cors:cors_option_filter_factory",  # BWC
        "ops_ping = nti.appserver.wsgi_ping:ping_handler_factory",
        "ops_identify = nti.app.authentication.wsgi_identifier:identify_handler_factory"
    ],
    "paste.server_runner": [
        "http = nti.appserver.standalone:server_runner",
        "gunicorn = nti.appserver.nti_gunicorn:paste_server_runner"
    ],
}

TESTS_REQUIRE = [
    # 2.0 is incompatible in a minor way with 1.4. It also pulls in six,
    # waitress, beautifulsoup4
    'WebTest',
    # A thin, practical wrapper around terminal coloring, styling, and
    # positioning. Pulled in by nose-progressive(?)
    'blessings >= 1.5.1',
    'coverage',  # Test coverage
    'fakeredis >= 0.4.1',
    'fudge',
    # easier access to the ipython debugger from nose, --ipdb; however,
    # messy with nose-progressive> consider pdbpp?
    'ipdb >= 0.8',
    'lupa', # needed by fakeredis when using lua
    'nose >= 1.3.0',
    'nose2',
    'nose-timer',
    'nose-progressive >= 1.5',
    # Nose integration: --pudb --pudb-failures. 0.1.2 requires trivial
    # patch
    'nose-pudb >= 0.1.2',
    'pyhamcrest >= 1.8.0',
    # ZODB in-memory conflict-resolving storage; like MappingStorage, but
    # handles changes
    'tempstorage >= 2.12.2',
    'zope.testing >= 4.1.2',
    'zope.testrunner',
    'nti.nose_traceback_info',
    'nti.testing',
    'nti.app.testing',
    'nti.fakestatsd'
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.dataserver',
    version=_read('version.txt').strip(),
    author='Jason Madden',
    author_email='jason@nextthought.com',
    description='NextThought Dataserver',
    long_description=(_read('README.rst') + '\n\n' + _read('CHANGES.rst')),
    license='Apache',
    keywords='web pyramid pylons',
    classifiers=[
        "Internet :: WWW/HTTP",
        'Intended Audience :: Developers :: Education',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Framework :: Pylons :: ZODB :: Pyramid',
        "Development Status :: 4 - Beta",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    url="https://github.com/NextThought/nti.dataserver",
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
        'nti.app.pyramid_zope',
        'nti.common',
        'nti.containers',
        'nti.contentfragments',
        'nti.contentprocessing',
        'nti.coremetadata',
        'nti.datastructures',
        'nti.dublincore',
        'nti.externalization',
        'nti.futures',
        'nti.geventwebsocket',
        'nti.i18n',
        'nti.identifiers',
        'nti.intid',
        'nti.links',
        'nti.mailer',
        'nti.metadata',
        'nti.mimetype',
        'nti.monkey',
        'nti.namedfile',
        'nti.ntiids',
        'nti.property',
        'nti.publishing',
        'nti.threadable',
        'nti.transactions',
        'nti.traversal',
        'nti.schema',
        'nti.site',
        'nti.utils',
        'nti.wref',
        'nti.zodb',
        'nti.zope_catalog',
        'objgraph',
        # Zope Acquisition; used by contentratings implicitly
        # cool concept. Pulls in ExtensionClass (which should only be
        # used for acquisition)
        'Acquisition',
        # (preferred) template rendering. pulled in by pyramid, but ensure latest version
        'Chameleon',
        'ExtensionClass',
        # fallback plain-text template render. pulled in by pyramid,
        # but ensure latest version
        'Mako',
        'RestrictedPython',
        'ZConfig',
        # Depending on the final release, we may need to explicitly
        # list each component.
        'ZODB',
        'BTrees',
        'zdaemon',
        'persistent',
        'ZEO',
        'RelStorage',
        'PyMySQL',
        'PyYAML',
        # pure-python cache for relstorage. Must set cache-module-name.
        # Needed for gevent
        'python-memcached',
        # See also http://pypi.python.org/pypi/neoppod/ for a
        # completely different option
        'appdirs',
        # 'appendonly >= 1.0.1', ZODB conflict-free structures featuring a Stack and more
        # See also blist for a tree-structured list
        # URL-safe "slugs" from arbitrary titles. Automatically
        # deals with several non-ASCII scripts
        'awesome-slugify',
        'bcrypt',
        'boto',     # amazon
        'brownie',     # Common utilities
        'cffi',  # Foreign Function Interface, libffi required
        # rating content objects (1.0-rc3 > 1.0 sadly, so specific)
        # See also collective.subscribe for a different take, useful when we need
        # this stuff globally
        # (https://github.com/collective/collective.subscribe/tree/master/collective/subscribe)
        # requires small patch to work without acquisition
        'contentratings',
        # 'cryptography', # oauthlib
        'cssselect',  # Used by pyquery
        'cython',
        # support for defining and evolving classes based on schemas
        # pulls in dm.reuse
        'dm.zope.schema',
        # gevent pure python dns resolving
        'dnspython',
        'filechunkio',  # Req'd for multi-put in boto == 2.5.2
        # A very simple (one module, no deps) RSS and Atom feed generator.
        # 1.7 is a modern rewrite with much better unicode and Py3k
        # support
        'feedgenerator',
        'futures',
        # We have a branch for this, installed in buildout.cfg
        'gevent',
        # pypy has its own greenlet implementation
        'greenlet',
        'gunicorn',
        # Redis C parser (almost certainly an anti-optimization on
        # PyPy)
        'hiredis ; platform_python_implementation == "CPython"',
        # gevent pure python dns resolving
        'idna',
        'isodate',     # ISO8601 date/time/duration parser and formatter
        # Simple helper library for signing data that roundtrips
        # through untrusted environments
        'itsdangerous',
        'logilab-common',
        # Powerful and Pythonic HTML/XML processing library combining
        # libxml2/libxslt with the ElementTree API. Also a pull parser.
        'lxml',
        'nameparser',  # Human name parsing
        # numpy is req'd by nltk, but not depended on. sigh.
        # This turns out to be because it CANNOT be installed in a setup.py:
        # Apparently it ships its own distutils. If you try to install from setup.py, you get
        # Warning: distutils distribution has been initialized, it may be too late to add a subpackage command
        # followed by compilation failures: fatal error 'Python.h' file not found. So you must
        # install numpy manually with pip: pip install numpy
        # or have it in requirements.txt (which we do).
        # It also works to install it with buildout, which is the currently
        # supported mechanism. This is how we do it with pypy too.
        'numpy',
        'packaging',
        'paste',
        'perfmetrics',  # easy statsd metrics.
        # much like zope.file, but some image-specific goodness.
        'premailer',  # inline css for html emails
        'psutil',
        'pyparsing',  # used by rdflib
        # Pure python PDF reading and manipulation library.
        'pyPDF2',
        'pyScss',
        # See also z3c.rml for a complete PDF layout and rendering environment, which should
        # work with page templates as well.
        # jquery-like traversing of python datastructures. lxml, cssselect
        # optional dependency on 'restkit' for interactive WSGI stuff
        # (used to be Paste)
        'pyquery',
        'pyramid',
        'pyramid_chameleon',
        'pyramid_mako',
        'pyramid_mailer',  # Which uses repoze.sendmail
        'pyramid_who',
        'pyramid_zcml',
        'pyramid-openid',
        # 'psycopg2 >= 2.5.1',    # PostGreSQL
        'pysaml2',
        # Monitoring stats and instrumenting code
        # statsd client. statsd must be installed separately:
        # https://github.com/etsy/statsd
        'python-statsd',
        # statsd server implementation, pure python. probably easier than setting up node. Might want to get it from https://github.com/sivy/py-statsd
        # Consider also https://github.com/phensley/gstatsd
        'pystatsd',
        'pytz',
        # Redis python client. Note that Amazon deployed servers are
        # still in the 2.6 (2.4?) series
        'redis',
        'reportlab',
        'repoze.lru',  # LRU caching. Dep of Pyramid
        'repoze.sendmail',  # trunk has some good binary changes
        'repoze.who >= 2.1',  #
        'repoze.zodbconn',
        # Requests: http for humans. Requests >= 1.0.x is depended on by httpie 0.4.
        # We use just the generic part of the API and work back to 0.14.
        # stripe also depends on just the minimal part of the api (their setup.py doesn't
        # give a version) (?). grequests 0.1.0 is not compatible with this.
        # If something used hooks, a change from 1.1 to 1.2 might
        # break it; no initial issues seen
        'requests',
        'setproctitle',     # used by gunicorn
        'setuptools',
        'simplejson',
        'six',
        'sympy',
        'supervisor',
        'transaction',
        'unicodecsv',
        # See http://pypi.python.org/pypi/user-agents/ for a high-level
        # library to do web user agent detection
        'webob',
        'z3c.appconfig',
        'z3c.autoinclude',
        # ZCML configurable local component registries
        'z3c.baseregistry',
        'z3c.batching',     # result paging. Pulled in by z3c.table
        'z3c.macro',
        'z3c.pagelet',
        'z3c.password',  # password policies
        # Better ZPT support than plastex, add-in to Chameleon
        'z3c.pt',
        # Make zope.pagetemplate also use the Chameleon-based ZPT
        'z3c.ptcompat',
        'z3c.rml',
        'z3c.schema',
        'z3c.table',     # Flexible table rendering
        'zc.catalog',
        'zc.displayname',  # Simple pluggable display name support
        'zc.intid >= 2.0.0',
        'zc.lockfile',
        'zc.queue',
        # compressed records. Will be built-in to newer ZODB
        'zc.zlibstorage',
        'zc.zodbdgc',
        'zodbpickle',
        'zope.app.broken',     # Improved broken objects
        # simple dependency tracking; re-exported from zope.container
        'zope.app.dependable',
        # Info about the app. currently unused
        'zope.applicationcontrol',
        'zope.annotation',
        'zope.authentication',
        # This is actually deprecated, use the ZODB import
        'zope.broken',
        'zope.browser',
        'zope.browserpage',
        'zope.browsermenu',  # Browser menu implementation for Zope.
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
        # 4.0.0a3 or greater is required in the 4 series
        'zope.container[zcml,zodb]',
        'zope.contentprovider',
        # A utility module for content-type handling.
        'zope.contenttype',
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
        'zope.file',     # zope.container dep
        'zope.formlib',  # Req'd by zope.mimetype among others,
        'zope.generations',
        # explicitly list this to ensure we get the fast C version.
        # Used by ZCA.
        'zope.hookable',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.index',
        'zope.interface',
        'zope.intid',
        'zope.keyreference',
        'zope.lifecycleevent',  # Object Added/Removed/etc events
        # Providers of Zope3 authentication.ILoginPassword for Zope3
        # publisher interfaces; pulled in by zope.file[test] and
        # indirectly zope.app.component[test]
        'zope.login',
        'zope.location',
        'zope.mimetype',
        'zope.minmax',
        'zope.pagetemplate',
        'zope.password',  # encrypted password management
        # pluggable authentication for zope.auth; see also repoze.who;
        # zope.container dependency
        'zope.pluggableauth',
        # Persistent, schema-based preferences with
        # site- and local defaults
        'zope.preference',
        'zope.ptresource',
        'zope.publisher',
        # Annotating principals in Zope3's global reg; pulled in
        # indirectly by zope.app.component[test]
        'zope.principalannotation',
        # Global principal registry component for Zope3
        'zope.principalregistry',
        'zope.processlifetime',
        # 4.1.x support py3k, uses newer APIs. Not binary compat with
        # older extensions, must rebuild. (In partic, req zope.security
        # >= 3.9)
        'zope.proxy',
        # DO NOT USED. Included as transitive for latest.
        'zope.sequencesort',  # advanced locale aware sorting
        'zope.schema',
        # >= 4.0.0b1 gets PyPy support!
        'zope.security[zcml,untrustedpython]',
        'zope.securitypolicy',
        'zope.session',  # 4.0.0a2 is out, should be fine
        'zope.site',  # local, persistent ZCA sites. zope.container dep
        'zope.size',
        # parser and renderers for the classic Zope "structured text" markup dialect (STX).
        # STX is a plain text markup in which document structure is signalled primarily by identation.
        # Pulled in by ...?
        'zope.structuredtext',
        # needed by nti.badges, we have monkey patches
        'zope.sqlalchemy',
        'zope.tal',
        'zope.tales',
        'zope.traversing',
        # Plug to make zope.schema's vocabulary registry ZCA
        # based and thus actually useful
        'zope.vocabularyregistry',
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
            # 'linesman >= 0.3.1',     # less that 0.3.0 conflicts with pillow (wanted PIL)
            # 'Pymacs >= 0.25', # checkout from git+https://github.com/pinard/Pymacs, run make. idiot thing uses a preprocessor, can't be directly installed
            #'dblatex >= 0.3.4',  # content rendering, convert docbook to tex. disabled due to sandbox violation
            'epydoc >= 3.0.1',  # auto-api docs
            'httpie',
            'jsonschema',
            'mistune',
            # the extra notebook is web based, pulls in tornado
            'ipython',
            'pip',
            #'pip-tools >= 0.3.4',     # command pip-review, pip-dump -- replaced by bin/checkversions
            # Python full screen console debugger. Beats ipython's:
            # import pudb; pdb.set_trace()
            'pudb >= 2013.5.1',
            'pylint',  # install astroid
            'pyramid_debugtoolbar >= 1.0.9',
            'repoze.sphinx.autointerface >= 0.7.1',
            'rope >= 0.9.4',  # refactoring library. c.f. ropemacs
            'ropemode >= 0.2',  # IDE helper for rope
            'ropemacs',
            'snakefood',  # dependency graphs
            # Narrative docs
            'sphinx',
            "sphinxcontrib-programoutput",
            # buildout
            'zc.buildout >= 2.2.1',
            # unused/used imports; see also tl.eggdeps
            'z3c.dependencychecker >= 1.11',
            'z3c.recipe.sphinxdoc',
            # Monitoring stats and instrumenting code
            # See above for python-statsd
            # 'graphite-web >= 0.9.10', # web front end. Requires the /opt/graphite directory. Pulls in twisted.
            # 'carbon >= 0.9.10', # storage daemon. Requires the /opt/graphite directory
            # 'whisper >= 0.9.10', # database lib.
            # See also https://github.com/hathawsh/graphite_buildout for a buildout to install node's statsd and graphite
            # locally (you may need to use a different version of node)
        ]
    },
    zip_safe=False,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    namespace_packages=['nti'],
    entry_points=entry_points,
)
