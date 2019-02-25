#!/usr/bin/env python
"""
zope.generations installer for nti.dataserver

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

generation = 102

# Allow going forward/backward for testing
import os
generation = int(os.getenv('DATASERVER_TEST_GENERATION', generation))

from zope.generations.generations import SchemaManager


class _DataserverSchemaManager(SchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        super(_DataserverSchemaManager, self).__init__(
            generation=generation,
            minimum_generation=generation,
            package_name='nti.dataserver.generations')


def evolve(context):
    result = install_main(context)
    install_chat(context)
    return result


from zope import component
from zope import interface
from zope import lifecycleevent

from zope.component.hooks import site

from zope.component.interfaces import ISite

import zope.intid

from zope.site import LocalSiteManager

from zope.site.folder import Folder, rootFolder

import zc.intid

import z3c.password.interfaces

import BTrees

from nti.containers import containers as container

from nti.contentfolder.index import install_content_resources_catalog

from nti.dataserver import users
from nti.dataserver import flagging
from nti.dataserver import _Dataserver
from nti.dataserver import session_storage
from nti.dataserver import password_utility
from nti.dataserver import shards as ds_shards

from nti.dataserver.interfaces import IOIDResolver
from nti.dataserver.interfaces import IUsersFolder
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IGlobalFlagStorage
from nti.dataserver.interfaces import ISessionServiceStorage
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.metadata.index import install_metadata_catalog

from nti.dataserver.users import index as user_index

from nti.dataserver.users.black_list import UserBlacklistedStorage

from nti.identifiers.index import install_identifiers_catalog

from nti.intid import utility as intid_utility

logger = __import__('logging').getLogger(__name__)


def install_chat(unused_context):
    pass


def install_main(context):
    conn = context.connection
    root = conn.root()

    # The root folder
    root_folder = rootFolder()
    # Ensure we have a connection so we can become KeyRefs
    conn.add(root_folder)
    # pylint: disable=protected-access
    assert root_folder._p_jar is conn

    # The root is generally presumed to be an ISite, so make it so
    # site is IRoot, so __base__ is the GSM
    root_sm = LocalSiteManager(root_folder)
    assert root_sm.__parent__ is root_folder
    assert root_sm.__bases__ == (component.getGlobalSiteManager(),)
    conn.add(root_sm)  # Ensure we have a connection so we can become KeyRefs
    assert root_sm._p_jar is conn

    root_folder.setSiteManager(root_sm)
    assert ISite.providedBy(root_folder)

    dataserver_folder = Folder()
    interface.alsoProvides(dataserver_folder, IDataserverFolder)
    conn.add(dataserver_folder)
    root_folder['dataserver2'] = dataserver_folder
    assert dataserver_folder.__parent__ is root_folder
    assert dataserver_folder.__name__ == 'dataserver2'
    assert root_folder['dataserver2'] is dataserver_folder

    lsm = LocalSiteManager(dataserver_folder)
    conn.add(lsm)
    assert lsm.__parent__ is dataserver_folder
    assert lsm.__bases__ == (root_sm,)
    # Change the dataserver_folder from IPossibleSite to ISite
    dataserver_folder.setSiteManager(lsm)
    assert ISite.providedBy(dataserver_folder)

    with site(dataserver_folder):
        assert component.getSiteManager() is lsm, \
               "Component hooks must have been reset"
        # from now on, operate in the site we're setting up.
        # The first thing that needs to happen is that we get
        # proper intid utilities set up so everything else
        # can get registered correctly.
        intids = install_intids(dataserver_folder)

        # Set up the shard directory, and add this object to it
        # Shard objects contain information about the shard, including
        # object placement policies (?). They live in the main database
        shards = container.LastModifiedBTreeContainer()
        dataserver_folder['shards'] = shards
        shards[conn.db().database_name] = ds_shards.ShardInfo()
        if conn.db().database_name == 'unnamed':
            logger.warn("Using an unnamed root database")
        assert shards[conn.db().database_name].__name__

        # The 'users' key should probably be several different keys, one for each type of
        # Entity object; that way traversal works out much nicer and dataserver_pyramid_views is
        # simplified through dropping UserRootResource in favor of normal traversal
        # These will become more than plain folders, they will.
        # become either zope.pluggableauth.plugins.principalfolder.PrincipalFolder
        # or similar implementations of IAuthenticatorPlugin.
        install_root_folders(dataserver_folder)

        # Install the site manager and register components
        root['nti.dataserver_root'] = root_folder
        root['nti.dataserver'] = dataserver_folder
        # The name that many Zope components assume
        root['Application'] = root_folder
        # the connection root doesn't fire events, do so for it
        lifecycleevent.added(root_folder)
        lifecycleevent.added(dataserver_folder)

        assert intids.getId(root_folder) is not None

        oid_resolver = _Dataserver.PersistentOidResolver()
        conn.add(oid_resolver)
        lsm.registerUtility(oid_resolver, provided=IOIDResolver)

        sess_storage = session_storage.OwnerBasedAnnotationSessionServiceStorage()
        lsm.registerUtility(sess_storage, provided=ISessionServiceStorage)

        install_user_catalog(dataserver_folder, intids)
        install_metadata_catalog(dataserver_folder, intids)
        install_identifiers_catalog(dataserver_folder, intids)
        install_context_lastseen_catalog(dataserver_folder, intids)
        install_content_resources_catalog(dataserver_folder, intids)

        users_folder = dataserver_folder['users']
        interface.alsoProvides(users_folder, IUsersFolder)

        everyone = users_folder['Everyone'] = users.Everyone()
        assert intids.getId(everyone) is not None
        assert everyone.username is not None

        install_flag_storage(dataserver_folder)

        install_password_utility(dataserver_folder)

        install_sites_folder(dataserver_folder)

        install_username_blacklist(dataserver_folder)
    return dataserver_folder


def install_intids(dataserver_folder):
    lsm = dataserver_folder.getSiteManager()
    # A utility to create intids for any object that needs it
    # Two choices: With either one of them registered, subscribers
    # fire forcing objects to be adaptable to IKeyReference.

    # intids = zope.intid.IntIds( family=BTrees.family64 )
    intids = intid_utility.IntIds('_ds_intid', family=BTrees.family64)
    intids.__name__ = '++etc++intids'
    intids.__parent__ = dataserver_folder
    lsm.registerUtility(intids, provided=zope.intid.IIntIds)
    # Make sure to register it as both types of utility, one is a subclass of
    # the other
    lsm.registerUtility(intids, provided=zc.intid.IIntIds)
    return intids


def install_context_lastseen_catalog(dataserver_folder, intids):
    try:
        from nti.app.users import index
        index.install_context_lastseen_catalog(dataserver_folder, intids)
    except ImportError:
        pass

def install_user_catalog(dataserver_folder, intids):
    return user_index.install_user_catalog(dataserver_folder, intids)


def install_password_utility(dataserver_folder):
    lsm = dataserver_folder.getSiteManager()
    policy = password_utility.HighSecurityPasswordUtility()
    policy.__name__ = '++etc++password_utility'
    policy.__parent__ = dataserver_folder
    policy.maxLength = 100
    policy.minLength = 6
    # The group max interferes with pass phrases, which we like
    policy.groupMax = 50
    lsm.registerUtility(policy,
                        provided=z3c.password.interfaces.IPasswordUtility)


def install_flag_storage(dataserver_folder):
    lsm = dataserver_folder.getSiteManager()
    lsm.registerUtility(flagging.IntIdGlobalFlagStorage(),
                        provided=IGlobalFlagStorage)


def install_root_folders(parent_folder,
                         folder_type=container.CaseInsensitiveLastModifiedBTreeFolder,
                         folder_names=('users',),
                         extra_folder_names=(),
                         exclude_folder_names=()):
    for key in (set(folder_names) | set(extra_folder_names)) - set(exclude_folder_names):
        parent_folder[key] = folder_type()
        parent_folder[key].__name__ = key


from zope.traversing.interfaces import IEtcNamespace

from nti.site.folder import HostSitesFolder


def install_sites_folder(dataserver_folder):
    """
    Given the IDataserverFolder, create the folder in which
    we will store persistent sites. This is also registered as an
    IEtcNamespace utility called \"hostsites\".
    """
    sites = HostSitesFolder()
    dataserver_folder['++etc++hostsites'] = sites
    lsm = dataserver_folder.getSiteManager()
    lsm.registerUtility(sites,
                        provided=IEtcNamespace, name='hostsites')


from nti.dataserver.interfaces import IShardLayout


def install_shard(root_conn, new_shard_name):
    """
    Given a root connection that is already modified to include a shard database
    connection having the given name, set up the datastructures for that new
    name to be a shard.
    """
    # The tests for this live up in appserver/account_creation_views
    root_layout = IShardLayout(root_conn)
    shards = root_layout.shards
    # pylint: disable=unsupported-membership-test
    if new_shard_name in shards:
        raise KeyError("Shard already exists", new_shard_name)

    shard_conn = root_conn.get_connection(new_shard_name)
    shard_root = shard_conn.root()

    # how much of the site structure do we need/want to mirror?
    # Right now, I'm making the new dataserver_folder a child of the main root folder and giving it
    # a shard name. But I'm not setting up any site managers
    root_folder = root_layout.root_folder

    dataserver_folder = Folder()
    interface.alsoProvides(dataserver_folder, IDataserverFolder)
    shard_conn.add(dataserver_folder)  # Put it in the right DB
    shard_root['nti.dataserver'] = dataserver_folder

    # make it a child of the root folder (TODO: Yes? This gets some cross-db stuff into the root
    # folder, which may not be good. We deliberately avoided that for the
    # 'shards' key)
    # pylint: disable=unsupported-assignment-operation
    root_folder[new_shard_name] = dataserver_folder
    shards[new_shard_name] = ds_shards.ShardInfo()

    # Put the same things in there, but they must not take ownership or generate
    # events
    install_root_folders(dataserver_folder,
                         folder_type=container.EventlessLastModifiedBTreeContainer)


def install_username_blacklist(dataserver_folder):
    """
    Given the IDataserverFolder, create the username blacklist btree, mapping
    case-insensitive usernames to their int-encoded delete time.
    """
    name = '++etc++username_blacklist'
    user_blacklist = UserBlacklistedStorage()
    user_blacklist.__name__ = name
    user_blacklist.__parent__ = dataserver_folder
    dataserver_folder[name] = user_blacklist

    lsm = dataserver_folder.getSiteManager()
    intids = lsm.getUtility(zope.intid.IIntIds)
    intids.register(user_blacklist)
    lsm.registerUtility(user_blacklist, provided=IUserBlacklistedStorage)
