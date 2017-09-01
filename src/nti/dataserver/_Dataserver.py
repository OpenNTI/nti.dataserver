#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import redis
import struct
import logging
from urlparse import urlparse

from zope import component
from zope import interface

import zope.deprecation as zope_deprecation

from zope.event import notify

from zope.interface.interfaces import ObjectEvent

from zope.intid.interfaces import IIntIds

from zope.processlifetime import DatabaseOpenedWithRoot

from ZODB.interfaces import IConnection

from persistent import Persistent

from nti.chatserver.chatserver import Chatserver

from nti.dataserver import config

from nti.dataserver.interfaces import SYSTEM_USER_ID
from nti.dataserver.interfaces import SYSTEM_USER_NAME

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver
from nti.dataserver.interfaces import IRedisClient
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IMemcacheClient
from nti.dataserver.interfaces import IDataserverClosedEvent
from nti.dataserver.interfaces import InappropriateSiteError

from nti.dataserver.meeting_container_storage import MeetingContainerStorage

from nti.dataserver.meeting_storage import CreatorBasedAnnotationMeetingStorage

from nti.dataserver.sessions import SessionService

from nti.externalization.interfaces import IExternalReferenceResolver

from nti.externalization.oids import fromExternalOID

from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import get_parts
from nti.ntiids.ntiids import escape_provider
from nti.ntiids.ntiids import is_ntiid_of_type
from nti.ntiids.ntiids import is_valid_ntiid_string

from nti.wref.interfaces import IWeakRef

# Note: There is a bug is some versions of the python interpreter
# such that initiating ZEO connections at the module level
# results in a permanant hang: the interpreter has two threads
# that are both waiting on either the GIL or the import lock,
# but something forgot to release it. The solution is to move this
# into its own function and call it explicitly.

DATASERVER_DEMO = 'DATASERVER_DEMO' in os.environ and 'DATASERVER_NO_DEMO' not in os.environ


def get_by_oid(oid_string, ignore_creator=False):
    resolver = component.queryUtility(IOIDResolver)
    if resolver is None:
        logger.warn("Using dataserver without a proper ISiteManager.")
    if resolver:
        return resolver.get_object_by_oid(oid_string, ignore_creator=ignore_creator)
    return None


@interface.implementer(IDataserverClosedEvent)
class DataserverClosedEvent(ObjectEvent):
    pass


@interface.implementer(IShardLayout)
class MinimalDataserver(object):
    """
    Represents the basic connections and nothing more.
    """

    db = None

    def __init__(self, parentDir=None):
        if parentDir is None and 'DATASERVER_DIR' in os.environ:
            parentDir = os.environ['DATASERVER_DIR']
        parentDir = os.path.expanduser(parentDir) if parentDir else parentDir
        self._parentDir = parentDir

        #: Either objects with a 'close' method, or a tuple of (object, method-to-call)
        self.other_closeables = []

        # TODO: We shouldn't be doing this, it should be passed to us, yes?
        self.conf = self._setup_conf(self._parentDir, DATASERVER_DEMO)

        # TODO: Used to register the IEnvironmentSettings in the registry, but
        # this seems to not be used anywhere
        # component.getGlobalSiteManager().registerUtility( self.conf )

        self.redis = self._setup_redis(self.conf)

        self._open_dbs()

        self.memcache = self._setup_cache(self.conf)
        if self.memcache is not None:
            self.other_closeables.append((self.memcache, self.memcache.disconnect_all))

        for deprecated in ('_setup_storage', '_setup_launch_zeo', '_setup_storages'):
            meth = getattr(self, deprecated, None)
            if meth is not None:  # pragma: no cover
                raise DeprecationWarning(deprecated +
                                         " is no longer supported. Remove your method " +
                                         str(meth))

    def _setup_conf(self, environment_dir, demo=False):
        return config.temp_get_config(environment_dir, demo=demo)

    def _open_dbs(self):
        if self.db is not None:
            self.db.close()

        # We don't actually want to hold a ref to any database except
        # the root database. All access to multi-databases should go
        # through an open connection.
        # TODO: 3 args for backwards compat
        self.db = self._setup_dbs(self._parentDir, None, None)

        # In zope, IDatabaseOpened is fired by
        # zope.app.appsetup.appsetup.
        # zope.app.appsetup.bootstrap.bootStrapSubscriber listens for
        # this event, and ensures that the database has a IRootFolder
        # object. Once that happens, then bootStrapSubscriber fires
        # IDatabaseOpenedWithRoot.

        # zope.generations installers/evolvers are triggered on
        # IDatabaseOpenedWithRoot We notify both in that same order
        # (sometimes action is taken on IDatabaseOpened which impacts
        # how zope.generations does its work on OpenedWithRoot).

        # First, connect_databases notifies DatabaseOpened (and AfterDatabaseOpened),
        # then we notify the OpenedWithRoot.

        notify(DatabaseOpenedWithRoot(self.db))

    def _setup_dbs(self, *unused_args):
        """
        Creates the database connections. Returns the root database.

        Notifies the database opened and after-database opened, but not
        the database-opened-with-root event.

        All arguments are ignored.
        """
        db = self.conf.connect_databases()  # Handles notifications, component registry
        return db

    def _setup_redis(self, conf):
        __traceback_info__ = self, conf, conf.main_conf
        if not conf.main_conf.has_option('redis', 'redis_url'):
            msg = """
            YOUR CONFIGURATION IS OUT OF DATE. Please install redis and then 
            run nti_init_env --upgrade-outdated --write-supervisord
            """
            logger.warn(msg)
            raise DeprecationWarning(msg)

        redis_url = conf.main_conf.get('redis', 'redis_url')
        parsed_url = urlparse(redis_url)
        if parsed_url.scheme == 'file':
            # Redis client doesn't natively understand file://, only redis://
            client = redis.StrictRedis(unix_socket_path=parsed_url.path)  # XXX Windows
        else:
            client = redis.StrictRedis.from_url(redis_url)
        interface.alsoProvides(client, IRedisClient)
        # TODO: Probably shouldn't be doing this
        component.getGlobalSiteManager().registerUtility(client, IRedisClient)
        return client

    def _setup_cache(self, conf):
        """
        Creates and returns a memcache instance to use.
        """

        # Import the python implementation
        import memcache
        cache_servers = conf.main_conf.get('memcached', 'servers')
        # That will throw a ConfigParser.Error if the config is out of date;
        # but in buildout, it should always be up-to-date

        cache = memcache.Client(cache_servers.split())
        logger.debug("Using MemCache servers at %s", cache_servers)

        import pickle
        cache.pickleProtocol = pickle.HIGHEST_PROTOCOL
        # TODO: also do that for any outstanding relstorage we can get to,
        # in each database and in each open connection, if any

        import threading
        # The underlying memcache object is not necessarily greenlet/thread safe
        # (it wants to be greenlet local, but that doesn't work well with long-lived
        # greenlets; see the monkey patch.) So we write an implementation that is
        # TODO: How much of a penalty do we take for this? We probably want a real
        # visible, manageable pool.

        @interface.implementer(IMemcacheClient)
        class _Client(object):

            def __init__(self, cache):
                self.cache = cache
                self.lock = threading.Lock()

            def get(self, *args, **kwargs):
                with self.lock:
                    return self.cache.get(*args, **kwargs)

            def set(self, *args, **kwargs):
                with self.lock:
                    return self.cache.set(*args, **kwargs)

            def delete(self, *args, **kwargs):
                with self.lock:
                    return self.cache.delete(*args, **kwargs)

        gsm = component.getGlobalSiteManager()
        gsm.registerUtility(_Client(cache), IMemcacheClient)
        # NOTE: This is not UDP based, it is TCP based, so we have to be careful
        # to close it. Our fork function uses disconnect_all, which simply
        # terminates the open sockets, if any; they all open back up
        # as needed in the children.
        return cache

    @property
    def dataserver_folder(self):
        """
        Returns an object implementing :class:`IDataserverFolder`.
        This object will have a parent implementing :class:`IRootFolder`
        """
        # We expect to be in a transaction and have a site manager
        # installed that came from the database
        lsm = component.getSiteManager()
        # zope.keyreference installs an IConnection adapter that
        # can traverse the lineage. That's important if we're using a nested,
        # transient site manager
        conn = IConnection(lsm, None)
        if conn:
            return conn.root()['nti.dataserver']

        raise InappropriateSiteError("Using Dataserver outside of site manager")

    @property
    def root(self):
        return self.dataserver_folder

    @property
    def root_folder(self):
        """
        Return an object implementing :class:`IRootFolder`
        """
        return self.dataserver_folder.__parent__

    @property
    def root_connection(self):
        """
        Returns the connection to the root database, the one containing the shard map.
        """
        return IConnection(self.dataserver_folder)

    @property
    def shards(self):
        """
        Returns the map of known database shards.
        """
        return self.dataserver_folder['shards']

    @property
    def users_folder(self):
        return self.dataserver_folder['users']

    def close(self):
        def _c(name, obj, close_func=None, level=logging.WARN):
            try:
                if close_func is None:
                    close_func = getattr(obj, 'close', None)
                if close_func is not None:
                    close_func()
                elif obj is not None:
                    logger.log(level, 
                               "Don't know how to close %s = %s", name, obj)
            except Exception:  # pylint:disable=I0011,W0703
                logger.log(level, 'Failed to close %s = %s',
                           name, obj, exc_info=True)

        # other_closeables were added after our setup completed, so they
        # could depend on us. Thus they need to be closed first.
        for o in self.other_closeables:
            c = None
            if isinstance(o, tuple):
                o, c = o
            _c(o, o, c)
        del self.other_closeables[:]

        # Now tear down us.
        # Close the root database. This closes its storage but leaves
        # all outstanding connections open (though useless)
        _c('self.db', self.db)
        # Close any multi databases. Recall, though, that the root database
        # is itself one of the multi-databases, so don't try to re-close it.
        # Depending on the status of any open transactions, there may be some connections
        # cached; these may or may not be able to be closed (RelStorage, in particular, causes
        # connections to raise an AttributeError; since this is expected, we
        # don't log it)
        for db_name, db in self.db.databases.items():
            if db is not self.db:
                _c(db_name, db, level=logging.DEBUG)

        _c('redis', self.redis, self.redis.connection_pool.disconnect)

        # Clean up what we did to the site manager
        gsm = component.getGlobalSiteManager()
        if gsm.queryUtility(IRedisClient) is self.redis:
            gsm.unregisterUtility(self.redis)
        notify(DataserverClosedEvent(self))

    def get_by_oid(self, oid_string, ignore_creator=False):
        return get_by_oid(oid_string, ignore_creator=ignore_creator)

    def _reopen(self):
        self._open_dbs()
        self._setup_redis(self.conf)


import functools

from nti.processlifetime import IAfterDatabaseOpenedEvent


@component.adapter(IAfterDatabaseOpenedEvent)
def _after_database_opened_listener(event):
    """
    After the database opened event has been fired, which
    lets :mod:`zope.app.broken` install a nice class
    factory for the database, we install a class factory
    that supports objects defining their own replacement,
    even if they aren't broken. This is useful for classes
    that used to be persistent but no longer are.
    """

    def _make_class_factory(db):
        """
        Support objects defining their own replacement object.
        This is useful for classes that used to be persistent but aren't anymore.
        """
        orig_class_factory = db.classFactory

        @functools.wraps(orig_class_factory)
        def nti_classFactory(connection, modulename, globalname):
            result = orig_class_factory(connection, modulename, globalname)
            replace = getattr(result, 
                              '_v_nti_pseudo_broken_replacement_name', 
                              None)
            if replace is not None:
                result = orig_class_factory(connection, modulename, replace)
            return result
        return nti_classFactory

    db = event.database
    db.classFactory = _make_class_factory(db)

    # Unfortunately, if a Connection was already opened, it
    # caches the class factory...and we would open a connection
    # to evolve the database. So we must go through and also
    # set those to the right value
    db.pool.map(lambda conn: setattr(conn._reader, '_factory', db.classFactory))

# After a fork, the dataserver has to be re-opened if it existed
# at the time of fork. (Note that if we are not preloading the app,
# then this config won't even be loaded in the parent process so this
# won't fire...still, be safe)


from nti.monkey import patch_random_seed_on_import
# since we'll be reseeding, make sure we get good seeds
patch_random_seed_on_import.patch()

from nti.processlifetime import IProcessDidFork


@component.adapter(IProcessDidFork)
def _process_did_fork_listener(unused_event):
    ds = component.queryUtility(IDataserver)
    if ds:
        # Re-open in place. pre-fork we called ds.close()
        ds._reopen()

    # Reseed the random number generator, especially for the use of
    # intid utilities. This should help reduce conflicts across worker
    # processes. (This is supposedly done by gunicorn in
    # workers.base.init_process, but it's not documented as such.)
    import random
    random.seed()

    # The zc.intid utility keeps a cache of the next id to use
    # in _v_nextid. However, we just closed and reopened the database,
    # so that volatile attribute will not be present

# close all resources at exit


def close_at_exit():
    ds = component.queryUtility(IDataserver)
    try:
        if ds:
            ds.close()
    except Exception:
        pass


import atexit
atexit.register(close_at_exit)


@interface.implementer(IDataserver)
class Dataserver(MinimalDataserver):

    chatserver = None
    session_manager = None

    def __init__(self, parentDir=None):
        super(Dataserver, self).__init__(parentDir)

        with self.db.transaction() as conn:
            root = conn.root()
            # Perform migrations
            # TODO: Adopt the standard migration package
            # TODO: For right now, we are also handling initialization until all code
            # is ported over
            if not root.has_key('nti.dataserver'):
                raise Exception("Creating DS against uninitialized DB. Test code?", 
                                str(root))

        self.__setup_volatile()

    def _reopen(self):
        super(Dataserver, self)._reopen()
        self.__setup_volatile()

    def __setup_volatile(self):
        # handle the things that need opened or reopened following a close
        self.session_manager = self._setup_session_manager()
        self.other_closeables.append(self.session_manager)

        self.chatserver = self._setup_chat()

        # Currently a no-op as we do this all in-process at the moment
        _, other_closeables = self._setup_change_distribution()

        self.other_closeables.extend(other_closeables or ())

    def _setup_change_distribution(self):
        """
        :return: A tuple of (changePublisherStream, [other closeables])
        """
        # To handle changes synchronously, we execute them before the commit happens
        # so that their changes are added with the main changes.
        # But this has to happen in the same greenlet, so this actually is a
        # no-op
        return (None, ())

    def _setup_session_manager(self):
        # The session service will read a component from our local site manager
        return SessionService()

    def _setup_chat(self):
        return Chatserver(self.session_manager,
                          meeting_storage=CreatorBasedAnnotationMeetingStorage(),
                          meeting_container_storage=MeetingContainerStorage())

    def get_sessions(self):
        return self.session_manager
    sessions = property(get_sessions)

    def close(self):
        super(Dataserver, self).close()


_SynchronousChangeDataserver = Dataserver
zope_deprecation.deprecated('_SynchronousChangeDataserver',
                            "Use plain Dataserver")


@interface.implementer(IExternalReferenceResolver)
@component.adapter(object, basestring)
def ExternalRefResolverFactory(_, __):
    ds = component.queryUtility(IDataserver)
    return _ExternalRefResolver(ds) if ds else None


class _ExternalRefResolver(object):

    def __init__(self, ds):
        self.ds = ds

    def resolve(self, oid):
        return self.ds.get_by_oid(oid)


@interface.implementer(IOIDResolver)
class PersistentOidResolver(Persistent):

    def get_object_by_oid(self, oid_string, ignore_creator=False):
        connection = IConnection(self)
        return get_object_by_oid(connection, oid_string, ignore_creator=ignore_creator)


def get_object_by_oid(connection, oid_string, ignore_creator=False):
    """
    Given an object id string as found in an OID value
    in an external dictionary, returns the object in the `connection` that matches that
    id, or None.

    :param ignore_creator: If True, then creator access checks will be
            bypassed.
    """
    # TODO: This is probably rife with possibilities for attack
    required_user_marker = connection
    required_user = None
    if is_ntiid_of_type(oid_string, TYPE_OID):
        parts = get_parts(oid_string)
        oid_string = parts.specific
        # The provider must be given. If it's the system user,
        # we'll ignore it. Otherwise, it must be checked. If it's not
        # present, then use a marker that will always fail.
        required_user = parts.provider or required_user_marker
    elif is_valid_ntiid_string(oid_string):
        # Hmm, valid but not an OID.
        logger.debug("Failed to resolve non-OID NTIID %s", oid_string)
        return None
    elif not oid_string:
        # Nothing given.
        return None

    oid_string, database_name, intid = fromExternalOID(oid_string)
    if not oid_string:
        logger.debug('No OID string given')
        return None

    __traceback_info__ = oid_string, database_name, intid
    try:
        if database_name:
            connection = connection.get_connection(database_name)

        # ZEO/FileStorage tends to rais KeyError here, and RelStorage can do that to.
        # RelStorage can also raise struct.error if the oid_string is not packed validly:
        # see ZODB.utils.u64.
        result = connection[oid_string]

        if IWeakRef.providedBy(result):
            result = result()

        if result is not None and intid is not None:
            obj = component.getUtility(IIntIds).getObject(intid)
            if obj is not result:
                raise KeyError("Mismatch between intid %s and %s", intid, obj)

        if result is not None and not ignore_creator:
            creator = getattr(result, 'creator', None)
            creator = getattr(creator, 'username', creator)
            creator_name = getattr(creator, 'id', creator)
            # Only the creator can access something it created.
            # Only the system user can access anything without a creator
            # (TODO: Should that change?)
            if creator_name != None:  # must check
                if escape_provider(creator_name) != required_user:
                    result = None
            elif required_user and required_user not in (SYSTEM_USER_NAME, SYSTEM_USER_ID):
                result = None

        return result
    except (KeyError, UnicodeDecodeError, struct.error):
        logger.exception("Failed to resolve oid '%s' using '%s'",
                         oid_string.encode('hex'), connection)
        return None
