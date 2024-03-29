#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for running the application with gunicorn.

You must use our worker (:class:`GeventApplicationWorker`), configured with paster::

    [server:main]
    use = egg:nti.dataserver#gunicorn
    host =
    port = %(http_port)s
    worker_class =  nti.appserver.nti_gunicorn.GeventApplicationWorker
    workers = 1

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,expression-not-assigned

import logging
logger = logging.getLogger(__name__)

from datetime import datetime

import os

from pyramid.threadlocal import get_current_request

import gunicorn.http.wsgi
import gunicorn.workers.ggevent as ggevent

from gunicorn.app.pasterapp import PasterServerApplication

if gunicorn.version_info not in ((19, 7, 1), (19, 8, 0), (19, 8, 1), (19, 9, 0)):
    raise ImportError("Unknown gunicorn version")

from gevent import getcurrent

from gunicorn.glogging import Logger as gunicorn_logger

from gunicorn.instrument.statsd import Statsd

from paste.deploy import loadwsgi

from nti.appserver.application_server import WebSocketServer


class GunicornLogger(gunicorn_logger):

    def atoms(self, resp, req, environ, request_time):
        #  * Make the 'u' variable actually do something
        #  * Add a custom atom (G) to get the greenlet id and pid
        #    into the message, just like in normal log messages.
        #  * Add a custom atom (C) to get the client identifer and version
        #  * Add a custom atom (R) to log connection pool info
        #  * Add a custom atom (S) to include current site name
        atoms = super(GunicornLogger, self).atoms(resp, req, environ, request_time)
        atoms['u'] = environ.get('REMOTE_USER', '-')
        atoms['G'] = "[%d:%d]" % (id(getcurrent()), os.getpid())

        client_app_id = environ.get('HTTP_X_NTI_CLIENT_APP', '-')
        client_version = environ.get('HTTP_X_NTI_CLIENT_VERSION', '-')
        atoms['C'] = "%s@%s" % (client_app_id, client_version)

        connection_pool = environ['nti_connection_pool']
        used_count = connection_pool.size - connection_pool.free_count()
        atoms['R'] = "(%s/%s)" % (used_count,
                                  connection_pool.size)
        current_site = environ.get('nti.current_site', '-')
        atoms['S'] = current_site
        return atoms

    def now(self):
        """
        Used when generating timestamps for the access log. Our
        superclass uses the standard Apache access log format but that
        doesn't include any partial seconds. The difference in
        precision on these access logs and the other log handlers
        creates issues when ordering and collating logs with tools
        like splunk.

        Force the times in gunicorns access logs to be a iso format
        using space seperator (which is easier when scanning).
        """
        _now = datetime.now()
        s = "[%s]" % _now.isoformat(sep=" ")
        return s


class GunicornStatsLogger(GunicornLogger, Statsd):
    """
    A gunicorn statsd logger.
    """


class _DummyApp(object):
    global_conf = None
    kwargs = None


def dummy_app_factory(global_conf, **kwargs):
    """
    A Paste app factory that exists to bootstrap the process
    in the master gunicorn instance. Individual worker instances will
    create their own application; the objects returned here simply
    echo configuration.
    """
    app = _DummyApp()
    app.global_conf = global_conf
    app.kwargs = kwargs
    return app


class _PhonyRequest(object):
    headers = ()
    input_buffer = None
    typestr = None
    uri = None
    path = None
    query = None
    method = None
    body = None
    scheme = 'http'  # added in 19.8.0
    version = (1, 0)
    proxy_protocol_info = None  # added in 0.15.0

    def get_input_headers(self):
        raise Exception("Not implemented for phony request")


from gunicorn.http import Request


class _NonParsingRequest(Request):
    def parse(self, unreader):
        pass

    @classmethod
    def unread(cls, buf):
        pass


import gevent


class _PyWSGIWebSocketHandler(WebSocketServer.handler_class, ggevent.PyWSGIHandler):
    """
    Our handler class combines pywsgi's custom logging and environment setup with
    websocket request upgrading. Order of inheritance matters.
    """

    # In gunicorn, an AsyncWorker defaults to handling requests itself, passing
    # them off to the application directly. Worker.handle goes to Worker.handle_request.
    # However, if you have a server_class involved, then that server entirely pre-empts
    # all the handling that the AsnycWorker would do. Since the Worker is what's aware
    # of the gunicorn configuration and calls gunicorn.http.wsgi.create to handle
    # getting the X-FORWARDED-PROTOCOL, etc, correct, it's important to do that.
    # Our worker uses a custom server, and we depend on that to be able to pass the right
    # information to gunicorn.http.wsgi.create

    __request = None

    def read_request(self, requestline):  # pylint: disable=arguments-differ
        self.__request = _NonParsingRequest(
            self.server.worker.cfg, _NonParsingRequest
        )
        self.requestline = requestline
        if self.__request.proxy_protocol(requestline):
            self.requestline = self.read_requestline()
        return super(_PyWSGIWebSocketHandler, self).read_request(self.requestline)

    def get_environ(self):
        # Start with what gevent creates
        environ = super(_PyWSGIWebSocketHandler, self).get_environ()
        # and then merge in anything that gunicorn wants to do instead
        request = _PhonyRequest()
        request.typestr = self.command
        request.uri = environ['RAW_URI']
        request.method = environ['REQUEST_METHOD']
        request.query = environ['QUERY_STRING']
        request.headers = []
        request.path = environ['PATH_INFO']
        request.body = environ['wsgi.input']
        if environ.get('SERVER_PROTOCOL') == 'HTTP/1.1':
            request.version = (1, 1)
        # start w/ wsgi
        request.scheme = environ.get('wsgi.url_scheme') or 'http'
        # set headers
        for header in self.headers.headers:
            # If we're not careful to split with a byte string here, we can
            # run into UnicodeDecodeErrors: True, all the headers are supposed to be sent
            # in ASCII, but frickin IE (at least 9.0) can send non-ASCII values,
            # without url encoding them, in the value of the Referer field (specifically
            # seen when it includes a fragment in the URI, which is also explicitly against
            # section 14.36 of HTTP 1.1. Stupid IE).
            k, v = header.split(':', 1)
            k = k.upper()
            v = v.strip()
            # add header
            request.headers.append((k, v))
            # check scheme
            if     (k == 'X-FORWARDED-PROTOCOL' and v == 'ssl') \
                or (k == 'X-FORWARDED-PROTO' and v == 'https') \
                or (k == 'X-FORWARDED-SSL' and v == 'on'):
                request.scheme = 'https'
        # The request arrived on self.socket, which is also environ['gunicorn.sock']. This
        # is the "listener" argument as well that's needed for deriving the
        # "HOST" value, if not present
        _, gunicorn_env = gunicorn.http.wsgi.create(request,
                                                    self.socket,
                                                    self.client_address,
                                                    self.socket.getsockname(),
                                                    self.server.worker.cfg)
        gunicorn_env.update(gunicorn.http.wsgi.proxy_environ(self.__request))
        environ.update(gunicorn_env)

        return environ


class GeventApplicationWorker(ggevent.GeventPyWSGIWorker):
    """
    Our application worker.
    """

    #: Our custom server requires a custom handler.
    wsgi_handler = _PyWSGIWebSocketHandler

    app = None
    socket = None
    policy_server = None

    PREFERRED_MAX_CONNECTIONS = 100

    @classmethod
    def setup(cls):  # pragma: no cover
        """
        We cannot patch the entire system to work with gevent due to
        issues with ZODB (but see application.py). Instead, we patch
        just our socket when we create it. So this method DOES NOT call
        super (which patches the whole system).
        """
        # But we do import the patches, to make sure we get the patches we do
        # want
        import nti.monkey.patch_gevent_on_import
        nti.monkey.patch_gevent_on_import.patch()

    def __init__(self, *args, **kwargs):  # pylint: disable=useless-super-delegation
        # These objects are instantiated by the master process (arbiter)
        # in the parent process, pre-fork, once for every worker
        super(GeventApplicationWorker, self).__init__(*args, **kwargs)
        # Now we have access to self.cfg and the rest

    def init_process(self, _call_super=True):  # pylint: disable=arguments-differ
        """
        We must create the appserver only once, and only after the
        process has forked if we are using ZEO; the monkey-patched
        greenlet threads that ZEO spawned are still stopped and
        shutdown after the fork. Something also goes wrong with the
        ClientStorage._cache; in a nutshell, we need to close and reopen
        the database.

        At one time, we had ZMQ background threads. So even if we
        have, say RelStorage and no ZEO threads, we could still fail
        to fork properly. In theory this restriction is lifted as of
        20130130, but that combo needs tested.

        An additional problem is that at DNS (socket.getaddrinfo and
        friends) hangs after forking if it was used *before* forking.
        The problem is that the default asynchronous resolver uses the
        hub's threadpool, which is initialized the first time it is
        used. Some bug prevents the threadpool from working after fork
        (it seems that the on_fork listener is not being called; if it
        gets called things work). The app startup sequence invokes DNS
        and thus inits the thread pool, so the DNS operations that
        happen after the fork fail---inparticular, starting the server
        accesses DNS and so we never get to the point of listening on
        the socket. One workaround for this is to manually re-init the
        thread pool if needed; another is to use the Ares resolver.
        For now, I'm attempting to re-init the thread pool. (TODO:
        This may be platform specific?)
        """
        # Patch up the thread pool and DNS if needed.
        # NOTE: This is too late to do this, it must be done before we need to reopen the
        # dataserver; thus it is done in the fork listener now, unconditionally

        # The Dataserver reloads itself automatically in the preload scenario
        # based on the post_fork and IProcessDidFork listener

        # Tweak the max connections per process if it is at the default (1000)
        # Large numbers of HTTP connections means large numbers of
        # database connections; multiply that by the number of processes and number
        # of machines, and we quickly run out. We probably can't really handle
        # 1000 simultaneous connections anyway, even though we are non-blocking
        worker_connections = self.cfg.settings['worker_connections']
        if (worker_connections.value == worker_connections.default
            and worker_connections.value >= self.PREFERRED_MAX_CONNECTIONS):
            worker_connections.set(self.PREFERRED_MAX_CONNECTIONS)
            self.worker_connections = self.PREFERRED_MAX_CONNECTIONS

        # Change/update the logging format.
        # It's impossible to configure this from the ini file because
        # Paste uses plain ConfigParser, which doesn't understand escaped % chars,
        # and tries to interpolate the settings for the log file.
        # For now, we just add on the time in seconds and  microseconds with %(T)s.%(D)s.
        # Other options include using a different key with a fake % char, like ^,
        # (Note: microseconds and seconds are not /total/, they are each fractions;
        # they come from a `datetime.timedelta` object, which guarantees that the
        # microsecond value is between 0 and one whole second; we need to properly set
        # formatting field width to account for this)
        # (Note: See below for why this must be sure to be a byte string: Frickin IE in short)
        self.cfg.settings['access_log_format'].set(
            str(self.cfg.access_log_format) + b" \"%(C)s\" \"%(S)s\" %(R)s %(G)s %(L)ss")

        # Also, if there is a handler set for the gunicorn access log (e.g., '-' for stderr)
        # Then the default propagation settings mean we get two copies of access logging.
        # make that stop.
        gun_logger = logging.getLogger('gunicorn.access')
        if gun_logger.handlers:  # pragma: no cover
            gun_logger.propagate = False

        self.server_class = _ServerFactory(self)

        gevent_trace = os.environ.get('gevent_trace')
        if gevent_trace:  # pragma: no cover
            def print_stacks():
                from nti.appserver._util import dump_stacks
                import sys
                while True:
                    gevent.sleep(15.0)
                    print('\n'.join(dump_stacks()), file=sys.stderr)

            gevent.spawn(print_stacks)

        # Everything must be complete and ready to go before we call into
        # the super, it in turn calls run()
        # NOTE: Errors here get silently swallowed and gunicorn just cycles the worker
        # (But at least as of 0.17.2 they are now reported? Check this.)
        if _call_super:  # pragma: no cover
            super(GeventApplicationWorker, self).init_process()


def make_WorkerGreenlet(pool):
    """
    Create the type of greenlet to use in the *pool*
    """
    # Top-level function for ease of testing.
    class WorkerGreenlet(pool.greenlet_class):
        """
        See nti.monkey for this. We provide a pretty thread name to the extent
        possible.
        """

        # Bind to self for ease of testing.
        get_current_request = staticmethod(get_current_request)

        __in_thread_name = False

        def __thread_name__(self):
            # The WorkerGreenlets themselves may be used to handle
            # multiple distinct requests in the case of HTTP
            # pipelining. The authentication information may
            # change between requests (in practice, that *should*
            # just be a transition between
            # authenticated/unauthenticated states for the same
            # user, but in theory it could be any transition, even across
            # users). Therefore, the request is the best place to cache.
            # Note that nti.transactions.pyramid_tween can retry requests,
            # using the same request object and environment.
            # pylint:disable=protected-access
            if self.__in_thread_name:
                # We're recursing. This happens when one of the request properties
                # calls back into this method, usually from logging.
                return '<recursing>'

            prequest = self.get_current_request()
            if not prequest:
                return self._formatinfo()

            try:
                return prequest._worker_greenlet_cached_thread_name
            except AttributeError:
                pass

            self.__in_thread_name = True
            try:
                cache = False
                try:
                    uid = prequest.unauthenticated_userid
                    cache = True
                except (LookupError, AttributeError):
                    # In some cases, pyramid tries to turn this into an authenticated
                    # user id, and if it's too early, we won't be able to use the dataserver
                    # (InappropriateSiteError)
                    # The AttributeError comes in due to what appears to be
                    # a race condition with local ZEO servers and very
                    # small connection pool sizes with very high request concurrency:
                    # objects seem to escape from the ZEO connection cache before
                    # __setstate__ has properly been filled in; typically
                    # this is the `lookup` attribute on a _LocalAdapterRegistry
                    # XXX: The above is almost certainly out of date.
                    uid = prequest.remote_user
            finally:
                del self.__in_thread_name

            result = "%s:%s" % (prequest.path, uid or '<NoUser>')
            if cache:
                prequest._worker_greenlet_cached_thread_name = result

            return result

    return WorkerGreenlet


class _ServerFactory(object):
    """
    Given a worker that has already created the app server, does
    what's necessary to finish initializing it for running (such as
    messing with socket blocking and adjusting handler classes).
    Serves as the 'server_class' value.
    """

    def __init__(self, worker):
        self.worker = worker

    def __call__(self,
                 listen_on_socket,
                 application=None,
                 spawn=None,
                 log=None,
                 handler_class=None,
                 environ=None):
        app_server = WebSocketServer(listen_on_socket,
                                     application,
                                     handler_class=handler_class or GeventApplicationWorker.wsgi_handler,
                                     environ=environ)
        # See _PyWSGIWebSocketHandler.get_environ # NOTE: Eliminate this
        app_server.worker = self.worker

        max_accept = os.environ.get('gevent_max_accept', None)
        if max_accept is not None:
            logger.info("Setting max_accept to %s", max_accept)
            app_server.max_accept = int(max_accept)
        elif self.worker.cfg.workers > 1:
            logger.info("Setting max_accept to 1")
            app_server.max_accept = 1

        # The worker will provide a Pool based on the
        # worker_connections setting
        assert spawn is not None
        spawn.greenlet_class = make_WorkerGreenlet(spawn)
        app_server.set_spawn(spawn)
        # We want to log with the appropriate logger, which
        # has monitoring info attached to it
        app_server.log = log

        # Stash the worker connection pool in the environ to see
        # how our connection pool is being used.
        app_server.environ['nti_connection_pool'] = app_server.pool

        app_server.environ['nti_worker_identifier'] = getattr(self.worker, '_nti_identifier', None)

        # Now, for logging to actually work, we need to replace
        # the handler class with one that sets up the required values in the
        # environment, as per ggevent.
        assert app_server.handler_class is _PyWSGIWebSocketHandler
        # One of our base classes likes to use base_env directly, even though
        # things have been merged into it, so provide a copy of that merge
        app_server.base_env = app_server.get_environ()
        return app_server


# Manage the forking events
from zope import interface
from zope import component

from zope.event import notify

from nti.processlifetime import ProcessDidFork
from nti.processlifetime import IProcessWillFork, ProcessWillFork


class _IGunicornWillFork(IProcessWillFork):
    """
    An event specific to gunicorn forking.
    """

    arbiter = interface.Attribute("The master arbiter")
    worker = interface.Attribute("The new worker that will run in the child")


class _IGunicornDidForkWillExec(interface.Interface):
    """
    An event specific to gunicorn sigusr2 handling.
    """
    arbiter = interface.Attribute(
        "The current master arbiter; will be going away")


_master_storages = {}


@interface.implementer(_IGunicornWillFork)
class _GunicornWillFork(ProcessWillFork):

    def __init__(self, arbiter, worker):
        self.arbiter = arbiter
        self.worker = worker


@interface.implementer(_IGunicornDidForkWillExec)
class _GunicornDidForkWillExec(object):

    def __init__(self, arbiter):
        self.arbiter = arbiter


_fork_count = 1

import transaction

from relstorage.storage import RelStorage

from zope.location.interfaces import ISublocations

from nti.dataserver.contenttypes.forums.interfaces import ITopic


def _cache_objects(db, pred=id):
    conn = db.open()

    def _act(k, seen=None):

        if seen is None:
            seen = set()

        if id(k) in seen:
            return
        seen.add(id(k))
        if ITopic.providedBy(k):
            return
        try:
            # pylint: disable=protected-access
            k._p_activate()
        except AttributeError:
            pass
        except KeyError:
            return

        subs = ISublocations(k, ())
        if subs:
            try:
                # pylint: disable=too-many-function-args
                subs = subs.sublocations()
            except LookupError:
                subs = ()

        try:
            for l in subs:
                _act(l, seen)
        except LookupError:
            pass

        try:
            for v in k.values():
                _act(v, seen)
        except (AttributeError, LookupError):
            pass

    seen = set()
    for user in conn.root()['nti.dataserver']['users'].values():
        # Activate each user and his sublocations
        if pred(user):
            _act(user, seen)

    transaction.abort()
    conn.close()


warm_cache = False


@component.adapter(_IGunicornWillFork)
def _process_will_fork_listener(unused_event):
    from nti.dataserver import interfaces as nti_interfaces
    ds = component.queryUtility(nti_interfaces.IDataserver)
    if ds:
        if warm_cache:
            try:
                # Prepopulate the cache before we fork to start all workers
                # off with an even keel.
                # This just ensures memcache is current, and
                # gets the bytes storage in place; it doesn't yet
                # do anything about connection level object caches
                if not _master_storages and isinstance(ds.db.storage.base, RelStorage):
                    logger.info("Warming cache in %s", os.getpid())
                    for name, db in ds.db.databases.items():
                        _master_storages[name] = db.storage
                    _cache_objects(ds.db)
                    logger.info("Done warming cache")
            except AttributeError:
                pass
        # Close the ds in the master, we don't need those connections
        # sticking around here. It will be reopened in the child
        ds.close()


from zope.processlifetime import IDatabaseOpened


@component.adapter(IDatabaseOpened)
def _replace_storage_on_open(event):

    if event.database.database_name in _master_storages:
        logger.info("Installing cached storage in pid %s: %s",
                    os.getpid(), _master_storages)
        event.database.storage = _master_storages[event.database.database_name]


from zope.processlifetime import IDatabaseOpenedWithRoot


@component.adapter(IDatabaseOpenedWithRoot)
def _cache_conn_objects(event):

    if event.database.database_name in _master_storages:
        logger.info("Caching objects in pid %s: %s",
                    os.getpid(), _master_storages)
        glts = [gevent.spawn(_cache_objects, event.database)
                for _ in range(event.database.pool.getSize())]
        gevent.joinall(glts)
        logger.info("Done caching objects in pid %s", os.getpid())


@component.adapter(_IGunicornDidForkWillExec)
def _process_did_fork_will_exec(event):
    # First, kill the DS for good measure
    _process_will_fork_listener(event)
    # Now, run component cleanup, etc, for good measure
    # First, ensure all cleanup hooks are in place.
    # This was probably needed due to https://github.com/zopefoundation/zope.component/pull/1
    # and can now be removed?
    from zope import site
    site = site
    from zope.testing import cleanup
    cleanup.cleanUp()


def _pre_fork(arbiter, worker):
    # We may or may not have the ZCA configuration, depending on prefork.
    # So things that MUST always happen, regardless, need to be here, not
    # in a listener
    # pylint: disable=global-statement

    # This is similar to arbiter.worker_age and worker.age but those aren't
    # documented in a way that looks like we can rely on them
    global _fork_count
    _fork_count += 1
    os.environ['DATASERVER_ZEO_CLIENT_NAME'] = 'gunicorn_' + str(_fork_count)

    worker._nti_identifier = str(_fork_count - 1)
    notify(_GunicornWillFork(arbiter, worker))


def _post_fork(unused_arbiter, worker):
    # Setup our environment variable now that we have actually forked.
    os.environ['NTI_WORKER_IDENTIFIER'] = worker._nti_identifier
    # Gunicorn forwarded allowed ips
    forwarded_ips = getattr(worker.cfg, 'forwarded_allow_ips', None)
    forwarded_ips = ','.join(forwarded_ips) if forwarded_ips else ''
    os.environ['NTI_FORWARDED_ALLOWED_IPS'] = forwarded_ips

    # See also
    # https://bitbucket.org/jgehrcke/gipc/src/bbfa4a02c756c81408e15016ad0ef836d1dcbad5/gipc/gipc.py?at=default#cl-217

    # Since we're in the child worker, go ahead and establish our signal handler
    # (the master wants to register a bunch of signals so we don't get a lot of choice;
    # even in the child worker they stick around)
    prev_handler = None

    import gc
    import sys
    import signal
    from nti.appserver._util import dump_info

    sigprof_id = '%s:%s' % (worker._nti_identifier, os.getpid())
    def handle_info(signum, frame):
        print('Handling SIGPROF to %s\n' % sigprof_id, file=sys.stderr)
        info = dump_info(db_gc=True)
        print(info, file=sys.stderr)
        print('\nGC Enabled:', gc.isenabled())
        if callable(prev_handler):
            prev_handler(signum, frame)

    prev_handler = signal.signal(signal.SIGPROF, handle_info)
    notify(ProcessDidFork())


def _pre_exec(arbiter):
    # Called during sigusr2 handling from arbiter.reexec(),
    # just after forking (and in the child process)
    # but before exec'ing the new master
    notify(_GunicornDidForkWillExec(arbiter))


class _PasterServerApplication(PasterServerApplication):  # pylint: disable=abstract-method
    """
    Exists to prevent loading of the app multiple times.
    """

    # Our base class never calls its super class's __init__ method,
    # which means attributes assigned there never get set. This in
    # turn means errors later on (such as when handling SIGHUP; this
    # particular error is worked around by implementing reload). This
    # is the set of missing attributes from 0.18.
    usage = None
    cfg = None
    prog = None
    logger = None

    # NOTE: The interaction between our server classes, our application classes,
    # gunicorn, and gevent is fairly complex and prone to breakage.
    # It seems like there's an opportunity to simplify some things;
    # auto-gen config files should help facilitate that.

    # pylint: disable=keyword-arg-before-vararg

    def __init__(self, app, gcfg=None, host="127.0.0.1", port=None,
                 *args, **kwargs):

        super(_PasterServerApplication, self).__init__(app, gcfg=gcfg, host=host,
                                                       port=port, *args, **kwargs)
        self.cfg.set('pre_fork', _pre_fork)
        self.cfg.set('post_fork', _post_fork)
        self.cfg.set('pre_exec', _pre_exec)
        if self.cfg.pidfile is None:
            # Give us a pidfile in the $DATASERVER_DIR var directory
            ds_dir = os.environ.get('DATASERVER_DIR')
            if ds_dir:
                pidfile = os.path.join(ds_dir, 'var', 'gunicorn.pid')
                self.cfg.set('pidfile', pidfile)

    def reload(self):
        # In super, reload calls load_config, which is only
        # implemented in the base.Application, not
        # PasterServerApplication, because PasterServerApplication
        # does all its config loading up-front in __init__. If we let
        # that happen, we wind up with missing configuration
        # information (not to mention running into NotImplemented
        # errors from the init() method of super), and ultimately, due
        # to the busted config, we stop listening on the socket.
        #
        # We're not (currently) worried about reloading configurations
        # from pserve.ini, we're mostly worried about things in ZCML
        # and the external resources they point to, like the library.
        # Therefor, the easiest thing to do when asked to reload is to
        # simply discard self.app, knowing that it will be asked for
        # again and in turn do the loading of the dataserver files.
        self.app = None  # Our copy
        self.callable = None  # base.Application's copy
        # Reset the component registry because we're about
        # to reconfigure it; otherwise we get Configuration errors
        from zope.testing import cleanup
        cleanup.cleanUp()
        return

    def load(self):
        if self.app is None:
            self.app = loadwsgi.loadapp(self.cfgurl, name='dataserver_gunicorn',
                                        relative_to=self.relpath)
        return self.app


# pylint: disable=keyword-arg-before-vararg

def paste_server_runner(unused_app, gcfg=None, host="127.0.0.1", port=None,
                        *args, **kwargs):
    """
    A paster server entrypoint.

    See :func:`gunicorn.app.pasterapp.paste_server`.
    """

    # Two arguments are passed by position, the application (as found
    # in the [app:main] section, usually), and the global
    # configuration dictionary (from the [DEFAULTS] section). All the
    # remainder are actually keyword arguments corresponding to the
    # setting values in the section that defined us ([server:main])

    _PasterServerApplication(None, gcfg=gcfg, host=host,
                             port=port, *args, **kwargs).run()
