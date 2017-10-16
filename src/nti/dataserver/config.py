#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Dataserver config routines

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# Patch for relstorage.
# MUST be done at a higher level
#import nti.monkey.relstorage_umysqldb_patch_on_import
# nti.monkey.relstorage_umysqldb_patch_on_import.patch()

import os
import stat
from six.moves import configparser
from six.moves import urllib_parse

try:
    from urllib.request import pathname2url
except ImportError:
    import urllib
    pathname2url = urllib.pathname2url

from zope import interface

from zope.event import notify

from zope.processlifetime import DatabaseOpened
from zope.processlifetime import DatabaseOpenedWithRoot

from nti.dataserver import interfaces as nti_interfaces

from nti.zodb.zlibstorage import install_zlib_client_resolver

logger = __import__('logging').getLogger(__name__)


def _file_contents_equal(path, contents):
    """
    :return: Whether the file at `path` exists and has `contents`
    """
    result = False
    if os.path.exists(path):
        with open(path, 'rU', 1) as f:
            path_contents = f.read()
            result = path_contents.strip() == contents.strip()

    return result


def write_configuration_file(path, contents, overwrite=True):
    """
    Ensures the contents of `path` contain `contents`.
    :param bool overwrite: If true (the default), existing files will be replaced. Othewise, existing
            files will not be modified.
    :return: The path.
    """
    if not overwrite and os.path.exists(path):
        return path

    if not _file_contents_equal(path, contents):
        # Must make the file
        logger.debug('Writing config file %s', path)
        try:
            os.mkdir(os.path.dirname(path))
        except OSError:
            pass
        with open(path, 'w') as f:
            print(contents, file=f)

    return path


class _Program(object):

    name = None
    cmd_line = None
    priority = 999

    def __init__(self, name, cmd_line=None):
        self.name = name
        if cmd_line is None:
            cmd_line = name
        self.cmd_line = cmd_line

    def get_command(self):
        return self.cmd_line

    def set_command(self, value):
        self.cmd_line = value
    command = property(get_command, set_command)


@interface.implementer(nti_interfaces.IEnvironmentSettings)
class _ReadableEnv(object):
    env_root = '/'
    settings = {}
    programs = ()

    def __init__(self, root='/', settings=None):
        self.env_root = os.path.abspath(os.path.expanduser(root))
        self.settings = settings if settings is not None else dict(os.environ)
        self.programs = []
        self._main_conf = None

    @property
    def main_conf(self):
        if self._main_conf is None:
            self._main_conf = configparser.SafeConfigParser()
            self._main_conf.read(self.conf_file('main.ini'))
        return self._main_conf

    def conf_file(self, name):
        return os.path.join(self.env_root, 'etc', name)

    def run_dir(self):
        return os.path.join(self.env_root, 'var')

    def run_file(self, name):
        return os.path.join(self.run_dir(), name)

    def data_dir(self):
        return os.path.join(self.env_root, 'data')

    def data_file(self, name):
        return os.path.join(self.data_dir(), name)

    def log_file(self, name):
        return os.path.join(self.env_root, 'var', 'log', name)


class _Env(_ReadableEnv):

    def __init__(self, root='/', settings=None, create=False, only_new=False):
        super(_Env, self).__init__(root=root, settings=settings)
        self.only_new = only_new
        if create:
            os.makedirs(self.env_root)
            os.makedirs(self.run_dir())
            os.makedirs(os.path.join(self.run_dir(), 'log'))

    def get_programs(self):
        return self.programs

    def add_program(self, program):
        self.programs.append(program)

    def write_main_conf(self):
        if self._main_conf is not None:
            with open(self.conf_file('main.ini'), 'wb') as fp:
                self._main_conf.write(fp)

    def write_conf_file(self, name, contents):
        """
        :return: The absolute path to the file written.
        """
        return write_configuration_file(self.conf_file(name), contents, overwrite=not self.only_new)

    def write_supervisor_conf_file(self, pserve_ini):

        ini = configparser.SafeConfigParser()
        ini.add_section('supervisord')
        ini.set('supervisord', 'logfile', self.log_file('supervisord.log'))
        ini.set('supervisord', 'loglevel', 'debug')
        ini.set('supervisord', 'pidfile', self.run_file('supervisord.pid'))
        ini.set('supervisord', 'childlogdir', self.run_file('log'))

        ini.add_section('unix_http_server')
        ini.set('unix_http_server', 'file', self.run_file('supervisord.sock'))

        ini.add_section('supervisorctl')
        ini.set('supervisorctl', 'serverurl', 'unix://' +
                self.run_file('supervisord.sock'))

        ini.add_section('rpcinterface:supervisor')
        ini.set('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                'supervisor.rpcinterface:make_main_rpcinterface')

        environment = ['DATASERVER_DIR=%(here)s/../',
                       'PYTHONHASHSEED=random']  # Secure random against DoS

        for p in self.programs:
            section = 'program:%s' % p.name
            ini.add_section(section)
            ini.set(section, 'command', p.cmd_line)
            if p.priority != _Program.priority:
                ini.set(section, 'priority', str(p.priority))
            ini.set(section, 'environment', ','.join(environment))

        with open(self.conf_file('supervisord.conf'), 'wb') as fp:
            ini.write(fp)

        # write dev config

        command = 'pserve'
        ini.add_section('program:pserve')
        ini.set('program:pserve', 'command', '%s %s' % (command, pserve_ini))
        ini.set('program:pserve', 'environment', ','.join(environment))
        ini.set('supervisord', 'nodaemon', 'true')
        with open(self.conf_file('supervisord_dev.conf'), 'wb') as fp:
            ini.write(fp)

        # write demo config
        environment.append('DATASERVER_DEMO=1')
        zeo_p = _create_zeo_program(self, 'demo_zeo_conf.xml')
        ini.set('program:zeo', 'command', zeo_p.cmd_line)
        ini.set('program:pserve', 'environment', ','.join(environment))
        for p in self.programs:
            section = 'program:%s' % p.name
            ini.set(section, 'environment', ','.join(environment))
        with open(self.conf_file('supervisord_demo.conf'), 'wb') as fp:
            ini.write(fp)


def _configure_redis(env):
    redis_file = env.run_file('redis.sock')
    redis_conf = env.conf_file('redis.conf')

    redis_conf_contents = []
    redis_conf_contents.append('port 0')  # turn off tcp
    redis_conf_contents.append('unixsocket ' + redis_file)  # activate unix sockets
    redis_conf_contents.append('loglevel notice')

    # Snapshotting
    redis_conf_contents.append("################################ SNAPSHOTTING  #################################")
    redis_conf_contents.append('dbfilename redis.dump.rdb')
    redis_conf_contents.append('dir ' + env.data_dir())

    redis_conf_contents.append("""# JAM: Note that the defaults, which are:
# Save the DB on disk:
#
#   save <seconds> <changes>
#
#   Will save the DB if both the given number of seconds and the given
#   number of write operations against the DB occurred.
#
#   In the example below the behaviour will be to save:
#   after 900 sec (15 min) if at least 1 key changed
#   after 300 sec (5 min) if at least 10 keys changed
#   after 60 sec if at least 10000 keys changed
#
#   Note: you can disable saving at all commenting all the "save" lines.
#save 900 1
#save 300 10
#save 60 10000

# JAM: Are probably insufficient for development purposes (few keys change,
# and restarts are rapid and often kill the redis server). Therefore, our default development configuration
# saves much *too* frequently for realworld use: every 30 seconds if anything has changed""")
    redis_conf_contents.append('save 30 1')

    env.write_conf_file('redis.conf', '\n'.join(redis_conf_contents))

    program = _Program('redis', '/opt/local/bin/redis-server ' + redis_conf)
    env.add_program(program)

    if not env.main_conf.has_section('redis'):
        env.main_conf.add_section('redis')
    env.main_conf.set('redis', 'redis_url', 
                      urllib_parse.urljoin('file://', pathname2url(redis_file)))


def _create_zeo_program(env_root, zeo_config='zeo_conf.xml'):
    program = _Program('zeo', 'runzeo -C ' + env_root.conf_file(zeo_config))
    program.priority = 0
    return program


def _configure_zeo(env_root):
    """
    :return: A list of URIs that can be passed to db_from_uris to directly connect
    to the file storages, without using ZEO.
    """
    def _mk_blobdir(blobDir):
        if not os.path.exists(blobDir):
            os.makedirs(blobDir)
            os.chmod(blobDir, stat.S_IRWXU)

    def _mk_blobdirs(datafile):
        blobDir = datafile + '.blobs'
        _mk_blobdir(blobDir)
        demoblobDir = datafile + '.demoblobs'
        _mk_blobdir(demoblobDir)
        return blobDir, demoblobDir

    dataFileName = 'data.fs'
    clientPipe = env_root.run_file("zeosocket")
    dataFile = env_root.data_file(dataFileName)
    blobDir, demoBlobDir = _mk_blobdirs(dataFile)

    configuration_dict = {
        'clientPipe': clientPipe, 'logfile': env_root.log_file('zeo.log'),
        'dataFile': dataFile, 'blobDir': blobDir,
    }

    configuration = """
        %%import zc.zlibstorage
        <zeo>
        address %(clientPipe)s
        </zeo>
        <serverzlibstorage>
        <filestorage 1>
        path %(dataFile)s
        blob-dir %(blobDir)s
        pack-gc false
        </filestorage>
        </serverzlibstorage>

        <eventlog>
        <logfile>
        path %(logfile)s
        format %%(asctime)s %%(message)s
        level DEBUG
        </logfile>
        </eventlog>
        """ % configuration_dict

    # NOTE: DemoStorage is NOT a ConflictResolvingStorage.
    # It will not run our _p_resolveConflict methods.
    demo_conf = configuration
    for i in range(1, 4):
        demo_conf = demo_conf.replace('<filestorage %s>' % i,
                                      '<demostorage %s>\n\t\t\t<filestorage %s>' % (i, i))
    demo_conf = demo_conf.replace(
        '</filestorage>', '</filestorage>\n\t\t</demostorage>')
    # Must use non-shared blobs, DemoStorage is missing fshelper.

    env_root.write_conf_file('zeo_conf.xml', configuration)
    env_root.write_conf_file('demo_zeo_conf.xml', demo_conf)

    # Now write a configuration for use with zc.zodbgc, which runs
    # much faster on raw files
    gc_configuration = """
        <zodb Users>
        <zlibstorage>
        <filestorage 1>
        path %(dataFile)s
        blob-dir %(blobDir)s
        pack-gc false
        </filestorage>
        </zlibstorage>
        </zodb>
        """ % configuration_dict
    env_root.write_conf_file('gc_conf.xml', gc_configuration)

    # Write one for ZEO access for online GC and diagnosis too
    gc_zeo_configuration = """
        <zodb Users>
        <zeoclient 1>
        storage 1
        server %(clientPipe)s
        blob-dir %(blobDir)s
        shared-blob-dir true
        </zeoclient>
        </zodb>
        """ % configuration_dict
    # TODO: Given this conf, and the possibilitiy of using zconfig:// urls in
    # repoze.zodbconn, maybe we should, on the DRY principal? Thus avoiding rewriting
    # stuff in the URI? The reason we haven't so far is the demo URIs differ by
    # blob dir
    env_root.write_conf_file('gc_conf_zeo.xml', gc_zeo_configuration)

    def _relstorage_stanza(name="Users", cacheServers=None,
                           blobDir=None,
                           addr=None,
                           db_name=None, db_username=None, db_passwd=None,
                           storage_only=False):
        if db_name is None:
            db_name = name
        if db_username is None:
            db_username = db_name
        if db_passwd is None:
            db_passwd = db_name

        DEFAULT_ADDR = "unix_socket /opt/local/var/run/mysql55/mysqld.sock"
        DEFAULT_CACHE = "localhost:11211"
        if addr is None:
            addr = DEFAULT_ADDR
        if cacheServers is None:
            cacheServers = DEFAULT_CACHE

        # Environment overrides
        if addr is DEFAULT_ADDR and 'MYSQL_HOST' in os.environ:
            addr = 'host ' + os.environ['MYSQL_HOST']

        if cacheServers is DEFAULT_CACHE and 'MYSQL_CACHE' in os.environ:
            cacheServers = os.environ['MYSQL_CACHE']

        if db_username is db_name and 'MYSQL_USER' in os.environ:
            db_username = os.environ['MYSQL_USER']

        if db_passwd is db_name and 'MYSQL_PASSWD' in os.environ:
            db_passwd = os.environ['MYSQL_PASSWD']

        # The value for shared-blob-dir is important. To quote the
        # RelStorage docs:
        # "If true (the default), the blob directory
        # is assumed to be shared among all clients using NFS or
        # similar; blob data will be stored only on the filesystem and
        # not in the database. If false, blob data is stored in the
        # relational database and the blob directory holds a cache of
        # blobs. When this option is false, the blob directory should
        # not be shared among clients."

        # Notice that we specify both a section name (<zodb Name>) and
        # the database-nome. Further explanation below.
        result = """
        <zodb %(name)s>
        pool-size 7
        cache-size 25000
        database-name %(name)s
        <zlibstorage>
        <relstorage %(name)s>
                blob-dir %(blobDir)s
                shared-blob-dir false
                cache-servers %(cacheServers)s
                cache-prefix %(db_name)s
                cache-module-name memcache
                poll-interval 0
                commit-lock-timeout 30
                keep-history false
                pack-gc false
                <mysql>
                    db %(db_name)s
                    user %(db_username)s
                    passwd %(db_passwd)s
                %(addr)s
                </mysql>
        </relstorage>
        </zlibstorage>
        </zodb>
        """ % locals()
        if storage_only:
            result = '\n'.join(result.splitlines()[4:-2])
        return result

    relstorage_configuration = """
    %%import relstorage
    %%import zc.zlibstorage
    %s
    """ % (_relstorage_stanza(blobDir=blobDir),)
    relstorage_zconfig_path = env_root.write_conf_file(
        'relstorage_conf.xml', relstorage_configuration)

    base_uri = 'zlibzeo://%(addr)s?storage=%(storage)s&database_name=%(name)s&blob_dir=%(blob_dir)s&shared_blob_dir=%(shared)s&connection_cache_size=25000&cache_size=104857600'
    file_uri = 'file://%s?database_name=%s&blobstorage_dir=%s'
    relstorage_zconfig_uri = 'zconfig://' + relstorage_zconfig_path

    uris = []
    demo_uris = []
    file_uris = []
    relstorage_uris = []
    for storage, name, data_file, blob_dir, demo_blob_dir in ((1, 'Users',    dataFile, blobDir, demoBlobDir),):

        uri = base_uri % {'addr': clientPipe, 'storage': storage,
                          'name': name, 'blob_dir': blob_dir, 'shared': True}
        uris.append(uri)

        uri = base_uri % {'addr': clientPipe, 'storage': storage,
                          'name': name, 'blob_dir': demo_blob_dir, 'shared': False}
        demo_uris.append(uri)

        file_uris.append(file_uri % (data_file, name, blob_dir))
        # NOTE: The ZConfig parser unconditionally lower cases the names of sections (e.g., <zodb Users> == <zodb users>)
        # While ZConfig doesn't alter the database-name attribute, repoze.zodbconn.resolvers ignores database-name
        # in favor of the section name. However, the database-name is what's used internally by the DB
        # objects to construct and follow the multi-database references. Not all tools suffer from this problem, though,
        # so section name and database-name have to match. The solution is to lowercase the fragment name in the URI.
        # This works because we then explicitly lookup databases by their complete, case-correct name when
        # we return them in a tuple. (Recall that we cannot change the database names once databases exist without
        # breaking all references, but in the future it would be a good idea to
        # name databases in lower case).
        relstorage_uris.append(relstorage_zconfig_uri + '#' + name.lower())

        convert_configuration = """
        <filestorage source>
            path %s
        </filestorage>
        %s
        """ % (data_file, _relstorage_stanza(name='destination', db_name=name, blobDir=blob_dir, storage_only=True))
        env_root.write_conf_file('zodbconvert_%s.xml' %
                                 name, convert_configuration)

        env_root.write_conf_file('relstorage_pack_%s.xml' % name, _relstorage_stanza(
            name=name, blobDir=blob_dir, storage_only=True))

    uri_conf = '[ZODB]\nuris = ' + ' '.join(uris)
    demo_uri_conf = '[ZODB]\nuris = ' + ' '.join(demo_uris)
    relstorage_uri_conf = '[ZODB]\nuris = ' + ' '.join(relstorage_uris)

    env_root.write_conf_file('zeo_uris.ini', uri_conf)
    env_root.write_conf_file('demo_zeo_uris.ini', demo_uri_conf)
    env_root.write_conf_file('relstorage_uris.ini', relstorage_uri_conf)

    # We assume that runzeo is on the path (virtualenv)
    program = _create_zeo_program(env_root, 'zeo_conf.xml')
    env_root.add_program(program)

    return file_uris


def db_from_uri(uris):
    # defer import for pypy
    # XXX: Drop this dependency and simply use
    # ZODB.config.databaseFromFile against zodb_conf.xml
    from repoze.zodbconn.uri import db_from_uri as _real_db_from_uri
    return _real_db_from_uri(uris)


def _configure_database_while_writing_config(env, uris):
    install_zlib_client_resolver()
    db = db_from_uri(uris)
    notify(DatabaseOpened(db))
    # Now, simply broadcasting the DatabaseOpenedWithRoot option
    # will trigger the installers from zope.generations...which
    # is ironic because the installers are what actually put the
    # root in place
    notify(DatabaseOpenedWithRoot(db))
    db.close()


def temp_get_config(root, demo=False, uri_name='zeo_uris.ini'):
    if not root:
        return None

    env = _Env(root, create=False)
    install_zlib_client_resolver()
    pfx = 'demo_' if demo else ''

    env.zeo_conf = env.conf_file(pfx + 'zeo_conf.xml')
    env.zeo_client_conf = env.conf_file(pfx + uri_name)
    env.zeo_launched = True
    ini = configparser.SafeConfigParser()
    ini.read(env.zeo_client_conf)
    env._ini = ini

    env.connect_databases = _make_connect_databases(env, root=root, ini=ini)
    return env


def temp_configure_database(root, uri_name='zodb_file_uris.ini'):
    env = temp_get_config(root, uri_name=uri_name)
    _configure_database_while_writing_config(env, env._ini.get('ZODB', 'uris'))


from zope import component

from ZODB.interfaces import IDatabase

from nti.processlifetime import AfterDatabaseOpenedEvent


def _make_connect_databases(env, ini=None, root=None):
    ini = {} if ini is None else ini

    def connect_databases():
        """
        Open and connect the ZODB databases configured.

        If this object has an attribute ``zeo_make_db``, then
        it should be a callable that returns a database. Otherwise,
        we will use the zeo_uris INI file.

        Side effects: Each ZODB DB opened is registered as a global
        component with its name (the 'Users' database is also
        registered as the default, unnamed utility if there is no
        unnamed database). Once that is done, the
        :class:`IDatabaseOpened` event is notified for each database
        (in no particular order). We then notify
        :class:`IAfterDatabaseOpenedEvent` for each database; this event
        comes before :class:`IDatabaseOpenedWithRoot` (which is only
        notified once, for the root database) and allows a chance for
        some application-specific bootstrap steps to be done. (Note
        that this method *does not* notify the root event, the caller
        should do that if the entire application is being
        bootstrapped.)

        :return: The root database (conventionally named Users).
        """
        __traceback_info__ = root, env.zeo_conf, env.zeo_client_conf, ini
        env.zeo_launched = True
        if not hasattr(env, 'zeo_uris'):
            env.zeo_uris = ini.get('ZODB', 'uris')
        if hasattr(env, 'zeo_make_db'):
            db = env.zeo_make_db()
        else:
            db = db_from_uri(env.zeo_uris)

        for name, xdb in db.databases.items():
            # Bug in ZODB: database doesn't declare it implements
            if not IDatabase.providedBy(xdb):
                interface.directlyProvides(xdb, IDatabase)
            component.getGlobalSiteManager().registerUtility(xdb, IDatabase, name)

        if '' not in db.databases:
            component.getGlobalSiteManager().registerUtility(db.databases['Users'], 
                                                             IDatabase)

        for xdb in db.databases.values():
            notify(DatabaseOpened(xdb))

        for xdb in db.databases.values():
            notify(AfterDatabaseOpenedEvent(xdb))

        # See notes in _configure_zeo about names and cases
        return db.databases['Users']

    return connect_databases


def write_configs(root_dir, pserve_ini, update_existing=False, write_supervisord=False):
    env = _Env(root_dir, create=(not update_existing),
               only_new=update_existing)
    uris = _configure_zeo(env)
    if not update_existing:
        _configure_database_while_writing_config(env, uris)

    _configure_redis(env)

    if not update_existing or write_supervisord:
        env.write_supervisor_conf_file(pserve_ini)
        env.write_main_conf()

    return env
