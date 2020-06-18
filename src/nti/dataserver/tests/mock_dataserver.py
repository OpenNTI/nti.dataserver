from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

# Things we don't care about:
# pylint:disable=protected-access,broad-except

# Things we do care about, but haven't had time to fix:
# pylint:disable=arguments-differ

import warnings
import tempfile
import shutil
import os
import unittest
from functools import wraps

import ZODB
from ZODB.DemoStorage import DemoStorage
from ZODB.FileStorage import FileStorage

from zope import component
from zope import interface
from zope.dottedname import resolve as dottedname

import zope.testing.cleanup

from nti.site.testing import persistent_site_trans
from nti.site.testing import uses_independent_db_site

from nti.testing import zodb
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin
from nti.testing.layers import find_test
from nti.testing.base import ConfiguringTestBase as _BaseConfiguringTestBase
from nti.testing.base import SharedConfiguringTestBase as _BaseSharedConfiguringTestBase

import nti.dataserver as dataserver
from nti.dataserver._Dataserver import Dataserver
from nti.dataserver.config import _make_connect_databases
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.tests import mock_redis

reset_db_caches = zodb.reset_db_caches # BWC. Used by nti/app/testing/webtest; remove when updated.

class IMockDataserver(nti_interfaces.IDataserver):
    """
    A mock dataserver.
    """

class MockConfig(object):
    zeo_conf = None
    zeo_client_conf = None
    connect_databases = None
    zeo_uris = ()
    zeo_launched = False
    zeo_make_db = None

@interface.implementer(IMockDataserver)
class ChangePassingMockDataserver(Dataserver):

    _mock_database = None
    #: A demo storage will be created on top of this
    #: storage. This can be used to create objects at
    #: class or module set up time and have them available
    #: to dataservers created at test method set up time.
    _storage_base = None

    def __init__(self, *args, **kwargs):
        self._storage_base = kwargs.pop('base_storage', None)
        super(ChangePassingMockDataserver, self).__init__(*args, **kwargs)

    def _setup_conf(self, *args, **kwargs):
        conf = MockConfig()
        conf.connect_databases = _make_connect_databases(conf)
        return conf

    def _setup_change_distribution(self):
        return (None, None)

    def _setup_session_manager(self, *args):
        pass

    def _setup_chat(self, *args):
        pass

    def _setup_redis(self, *args):
        client = mock_redis.InMemoryMockRedis()
        component.provideUtility(client)
        return client

    def _setup_cache(self, *args):
        return None

    def _setup_dbs(self, *args):
        self.conf.zeo_uris = ["memory://1?database_name=Users&demostorage=true",]
        self.conf.zeo_launched = True

        if self._mock_database:
            # Replace the connect function with this trivial one
            self.conf.zeo_make_db = lambda: self._mock_database
        else:
            # DemoStorage supports blobs if its 'changes' storage supports blobs or is not given;
            # a plain MappingStorage does not.
            # It might be nice to use TemporaryStorage here for the 'base', but it's incompatible
            # with DemoStorage: It raises a plain KeyError instead of a POSKeyError for missing
            # objects, which breaks DemoStorages' base-to-change handling logic
            # Blobs are used for storing "files", which are used for image data, which comes up
            # in at least evolve25
            self.conf.zeo_make_db = lambda: ZODB.DB(DemoStorage(base=self._storage_base),
                                                    database_name='Users')

        return super(ChangePassingMockDataserver, self)._setup_dbs(*args)


MockDataserver = ChangePassingMockDataserver


def add_memory_shard(mock_ds, new_shard_name):
    """
    Operating within the scope of a transaction, add a new shard with the given
    name to the configuration of the given mock dataserver.
    """

    new_db = ZODB.DB(DemoStorage(), databases=mock_ds.db.databases, database_name=new_shard_name)

    current_conn = mock_ds.root._p_jar
    installer = dottedname.resolve('nti.dataserver.generations.install.install_shard')

    installer(current_conn, new_db.database_name)

current_mock_ds = None


def _mock_ds_wrapper_for(func,
                         factory=MockDataserver,
                         teardown=None,
                         base_storage=None):

    @uses_independent_db_site(db_factory=lambda: current_mock_ds.db)
    @wraps(func)
    def install_dataserver_and_run(*args):
        global current_mock_ds # XXX Make this a layer/class property # pylint:disable=global-statement
        ds = current_mock_ds
        component.provideUtility(ds, nti_interfaces.IDataserver)
        assert component.getUtility(nti_interfaces.IDataserver)
        try:
            func(*args)
        finally:
            # We're not worried about cleaning up the registration,
            # the site we registered it in is transient.
            current_mock_ds = None
            ds.close()
            if teardown:
                teardown()

    @wraps(func)
    def f(*args):
        global current_mock_ds # XXX Make this a layer/class property # pylint:disable=global-statement
        # XXX: base_storage appears to be unused, always None
        ds = factory(base_storage=base_storage(*args) if callable(base_storage) else base_storage)
        current_mock_ds = ds
        return install_dataserver_and_run(*args)

    return f

def WithMockDS(*args, **kwargs):
    """

    :keyword base_storage: Either a storage instance that
        will be used as the underlying storage for DemoStorage,
        thus allowing some state to be reused, or a callable
        taking the same arguments as the the function being
        wrapped that returns a storage.

    """

    teardown = lambda: None
    if len(args) == 1 and not kwargs:
        # Being used as a plain decorator
        func = args[0]

        return _mock_ds_wrapper_for(func)

    # Being used as a decorator factory
    mock_ds_factory = MockDataserver
    if kwargs.get('with_changes', None):
        warnings.warn('with_changes is deprecated', DeprecationWarning, stacklevel=2)
        mock_ds_factory = ChangePassingMockDataserver

    if 'database' in kwargs:
        database = kwargs.pop('database')
        def factory(*args, **kwargs):
            md = mock_ds_factory.__new__(mock_ds_factory)
            md._mock_database = database
            md.__init__()
            return md
    elif 'temporary_filestorage' in kwargs and kwargs['temporary_filestorage']:

        td = tempfile.mkdtemp()
        teardown = lambda: shutil.rmtree(td, ignore_errors=True)
        def factory(*args, **kmargs):

            databases = {}
            db = ZODB.DB(FileStorage(os.path.join(td, 'data'), create=True),
                         databases=databases,
                         database_name='Users')
            md = mock_ds_factory.__new__(mock_ds_factory)
            md._mock_database = db
            md.__init__()
            return md
    elif 'factory' in kwargs:
        factory = kwargs.pop('factory')
    else:
        factory = mock_ds_factory

    return lambda func: _mock_ds_wrapper_for(func, factory, teardown,
                                             base_storage=kwargs.get('base_storage'))

current_transaction = None



class mock_db_trans(persistent_site_trans):
    """
    A context manager that returns a connection. Use
    inside a function decorated with :class:`WithMockDSTrans`
    or similar.
    """
    conn = None

    def __init__(self, ds=None, site_name=None):
        """
        :keyword site_name: If given, names a site (child of the ds site)
            that will be made current during execption.
        """
        self.ds = ds or current_mock_ds
        super(mock_db_trans, self).__init__(self.ds.db, site_name)

    def on_connection_opened(self, conn):
        super(mock_db_trans, self).on_connection_opened(conn)
        global current_transaction # XXX Refactor # pylint:disable=global-statement
        current_transaction = conn

        component.provideUtility(self.ds, nti_interfaces.IDataserver)
        assert component.getUtility(nti_interfaces.IDataserver)

        return conn

    def __exit__(self, t, v, tb):
        global current_transaction # XXX Refactor  # pylint:disable=global-statement
        return super(mock_db_trans, self).__exit__(t, v, tb)

def WithMockDSTrans(func):

    @wraps(func)
    def with_mock_ds_trans(*args, **kwargs):
        global current_transaction # XXX Refactor # pylint:disable=global-statement
        global current_mock_ds # XXX Refactor # pylint:disable=global-statement
        # Previously, we setHooks() here and resetHooks()
        # in the finally block. Setting is fine, and we do have to have
        # them in place to run the ds, but resetting them here
        # interferes with fixtures (layers) that assume they can
        # set the hooks just once, so we musn't reset them.
        # All fixtures now setHooks() before running, so no
        # need to even do that anymore.
        # setHooks()

        ds = MockDataserver() if not getattr(
            func, 'with_ds_changes', False
        ) else ChangePassingMockDataserver()
        current_mock_ds = ds

        try:
            with mock_db_trans(ds):
                func(*args, **kwargs)
        finally:
            current_mock_ds = None
            current_transaction = None
            ds.close()
            # see comments above
            # resetHooks()

    return with_mock_ds_trans

class _TestBaseMixin(object):
    set_up_packages = (dataserver,)

    @property
    def ds(self):
        return current_mock_ds


class ConfiguringTestBase(_TestBaseMixin,
                          _BaseConfiguringTestBase):
    """
    A test base that does two things: first, sets up the :mod:`nti.dataserver` module
    during setUp, and second, makes the value of :data:`current_mock_ds` available
    as a property on this object (when used inside a function decorated with :func:`WithMockDS`
    or :func:`WithMockDSTrans`).
    """


class SharedConfiguringTestBase(_TestBaseMixin,
                                _BaseSharedConfiguringTestBase):
    """
    A test base that does two things: first, sets up the :mod:`nti.dataserver` module
    during class setup, and second, makes the value of :data:`current_mock_ds` available
    as a property on this object (when used inside a function decorated with :func:`WithMockDS`
    or :func:`WithMockDSTrans`).
    """


class DSInjectorMixin(object):

    @classmethod
    def setUpTestDS(cls, test=None):
        test = test or find_test()
        if isinstance(type(test), type) and 'ds' not in type(test).__dict__:
            type(test).ds = _TestBaseMixin.ds


class DataserverTestLayer(ZopeComponentLayer,
                          ConfiguringLayerMixin,
                          DSInjectorMixin):
    """
    A test layer that does two things: first, sets up the
    :mod:`nti.dataserver` module during class setup. Second, if the
    test instance and test class have no ``ds`` attribute, a property
    is mixed in to provide access to the the value of
    :data:`current_mock_ds` available as a property on this object
    (when used inside a function decorated with :func:`WithMockDS` or
    :func:`WithMockDSTrans`).
    """

    set_up_packages = ('nti.dataserver',)

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        test = test or find_test()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass


class DataserverLayerTest(_TestBaseMixin,
                          unittest.TestCase):
    layer = DataserverTestLayer

SharedConfiguringTestLayer = DataserverTestLayer # bwc


class NotDevmodeSharedConfiguringTestLayer(ZopeComponentLayer,
                                           ConfiguringLayerMixin,
                                           DSInjectorMixin):
    """
    A test layer that does two things: first, sets up the
    :mod:`nti.dataserver` module during class setup (with no features). Second, if the
    test instance and test class have no ``ds`` attribute, a property
    is mixed in to provide access to the the value of
    :data:`current_mock_ds` available as a property on this object
    (when used inside a function decorated with :func:`WithMockDS` or
    :func:`WithMockDSTrans`).
    """

    #description = "nti.dataserver is ZCML configured without devmode"

    set_up_packages = ('nti.dataserver',)
    features = ()

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        test = test or find_test()
        cls.setUpTestDS(test)

class NotDevmodeDataserverLayerTest(_TestBaseMixin,
                                    unittest.TestCase):
    layer = NotDevmodeSharedConfiguringTestLayer
