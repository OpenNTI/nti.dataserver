#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import string
import functools

from six import string_types

import transaction

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.cachedescriptors.property import CachedProperty

from zope.event import notify as do_notify

from zope.intid.interfaces import IIntIds

from zope.keyreference.interfaces import IKeyReference

from ZODB.interfaces import IConnection

from ZODB.POSException import ConnectionStateError

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import ILastModified
from nti.dataserver.interfaces import INewUserPlacer
from nti.dataserver.interfaces import SYSTEM_USER_NAME

from nti.dataserver.users.interfaces import IDoNotValidateProfile
from nti.dataserver.users.interfaces import IRequireProfileUpdate
from nti.dataserver.users.interfaces import UsernameCannotBeBlank
from nti.dataserver.users.interfaces import WillDeleteEntityEvent
from nti.dataserver.users.interfaces import WillUpdateEntityEvent
from nti.dataserver.users.interfaces import IImmutableFriendlyNamed
from nti.dataserver.users.interfaces import WillCreateNewEntityEvent
from nti.dataserver.users.interfaces import WillUpdateNewEntityEvent
from nti.dataserver.users.interfaces import IUserProfileSchemaProvider
from nti.dataserver.users.interfaces import UsernameContainsIllegalChar

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.internalization import notify_modified
from nti.externalization.internalization import update_from_external_object

from nti.ntiids.ntiids import DATE
from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import escape_provider
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

logger = __import__('logging').getLogger(__name__)


def get_shared_dataserver(context=None, default=None):
    if default != None:
        return component.queryUtility(IDataserver, context=context, default=default)
    return component.getUtility(IDataserver, context=context)


def named_entity_ntiid(entity):
    return make_ntiid(date=DATE,
                      provider=SYSTEM_USER_NAME,
                      nttype=entity.NTIID_TYPE,
                      specific=escape_provider(entity.username.lower()))


@functools.total_ordering
@interface.implementer(IEntity, ILastModified, IAttributeAnnotatable)
class Entity(PersistentCreatedModDateTrackingObject):
    """
    The root for things that represent human-like objects.
    """

    _ds_namespace = 'users'  # TODO: This doesn't really belong here

    @classmethod
    def get_entity(cls, username, dataserver=None, default=None, _namespace=None):
        """
        Returns an existing entity with the given username or None. If the
        dataserver is not given, then the global dataserver will be used.

        :param basestring username: The username to find. If this string is actually
                an ntiid, then an entity will be looked up by ntiid. This permits
                finding user-specific objects like friends lists.
        :raises TypeError: If the username is not a valid username string.
        """
        if username is None:
            return default

        if is_valid_ntiid_string(username):
            result = find_object_with_ntiid(username)
            if result is not None:
                if not isinstance(result, Entity):
                    result = None
                return result or default

        dataserver = dataserver or get_shared_dataserver(default=default)
        if dataserver is not default:
            # Sometimes we get a dict sneaking in here when updating from external objects.
            # The CaseInsensitiveLastModifiedBTreeFolder turns out to throw a TypeError
            # in that case, the same thing that, say, BTrees.IIBTree.IIBTree
            # does
            ns = _namespace or cls._ds_namespace
            return dataserver.root[ns].get(username, default)
        return default

    @classmethod
    def create_entity(cls, dataserver=None, **kwargs):
        """
        Creates (and returns) and places in the dataserver a new entity,
        constructed using the keyword arguments given, the same as those
        the User constructor takes. If an user already exists with that name,
        raises a :class:`KeyError`. You handle the transaction.

        The newly-created user will be placed in a shard through use of a
        :class:`..interfaces.INewUserPlacer`. If the unnamed (default)
        utility is available, it will be used. Otherwise, the utility named
        ``default`` (which is configured by this package) will be used.

        This method fires :class:`.interfaces.IWillUpdateNewEntityEvent`,
        :class:`.interfaces.IWillCreateNewEntityEvent`,
        :class:`zope.lifecycleevent.IObjectCreatedEvent` and
        :class:`zope.lifecycleevent.IObjectAddedEvent`, in that order.

        :keyword dict external_value: Optional dictionary used to update the object
                through the user externalization mechanisms. This is done
                before the user is stored anywhere and any added/created events are
                fired. No notifications are emitted during this process.
        :keyword bool preflight_only: If ``False`` (the default), the user is created
                as normal. If set to ``True``, then the process stops before the
                :class:`zope.lifecycleevent.IObjectCreated` and
                :class:`zope.lifecycleevent.IObjectAdded` events are fired, and the user
                object is not actually added to the database. When ``True``, the preflight
                object is returned (assuming validation went as planned),
                but it will not have a valid ``__parent__``
        """

        dataserver = dataserver or get_shared_dataserver()
        root_users = dataserver.root[cls._ds_namespace]
        preflight_only = kwargs.pop('preflight_only', False)

        if 'parent' not in kwargs:
            kwargs['parent'] = root_users
        __traceback_info__ = kwargs

        # When we auto-create users, we need to be sure
        # they have a database connection so that things that
        # are added /to them/ (their contained storage) in the same transaction
        # will also be able to get a database connection and hence
        # an OID.
        # NOTE: This is also where we decide which database shard the user lives in
        # First we create the skeleton object
        user = cls.__new__(cls)
        user.username = kwargs['username']

        # Then we place it in a database. It's important to do this before any code
        # runs so that subobjects which might go looking through their parents
        # to find a IConnection find the user's IConnection *first*, before they find
        # the `root_users` connection
        if not preflight_only:
            placer = component.queryUtility(INewUserPlacer) \
                  or component.getUtility(INewUserPlacer, name='default')
            placer.placeNewUser(user, root_users, dataserver.shards)

            IKeyReference(user)  # Ensure it gets added to the database
            assert getattr(user, '_p_jar', None), \
                   "User should have a connection"

        # Take out some extra arguments used during the
        # creation process from external data but
        # not internally. Site policies and the like will
        # look for, and possibly modify these, so ensure
        # that we have one dictionary throughout the process
        meta_data = kwargs.pop('meta_data', {})
        ext_value = kwargs.pop('external_value', {})

        # Finally, we init the user
        user.__init__(**kwargs)
        assert preflight_only or getattr(user, '_p_jar', None), \
               "User should still have a connection"

        # Notify we're about to update
        do_notify(WillUpdateNewEntityEvent(user, ext_value, meta_data))

        # Update from the external value, if provided
        if ext_value:
            update_from_external_object(user, ext_value,
                                        context=dataserver, notify=False)

        # Register an intid for this user that we are creating so that the events that fire before
        # ObjectAdded (which is usually when intids get assigned) can use it.
        component.getUtility(IIntIds).register(user)
        do_notify(WillCreateNewEntityEvent(user, ext_value, preflight_only, meta_data))

        if preflight_only:
            if user.username in root_users:
                raise KeyError(user.username)
            user.__parent__ = None

            # Be sure we didn't add this guy anywhere. If we did, then things are
            # wacked and we need this transaction to fail.
            assert getattr(user, '_p_jar', None) is None, \
                   "User should NOT have a connection"

            # Must NOT try to commit the transaction since the object has been
            # added to the intid registry
            transaction.doom()
            return user

        lifecycleevent.created(user)  # Fire created event

        # Must manually fire added event if parent was given
        if kwargs['parent'] is not None:
            lifecycleevent.added(user, kwargs['parent'], user.username)

        # Now store it. If there was no parent given or parent was none,
        # this will fire ObjectAdded. If parent was given and is different than root_users,
        # this will fire ObjectMoved. If the user already exists, raises a
        # KeyError
        root_users[user.username] = user
        return user

    @classmethod
    def delete_entity(cls, username, dataserver=None):
        """
        Delete the entity (in this class's namespace) given by `username`. If the entity
        doesn't exist, raises :class:`KeyError`.
        :return: The user that was deleted.
        """

        dataserver = dataserver or get_shared_dataserver()
        root_users = dataserver.root[cls._ds_namespace]
        user = root_users[username]

        do_notify(WillDeleteEntityEvent(user))

        del root_users[username]

        # Also clean it up from whatever shard it happened to come from
        home_shard = IShardLayout(IConnection(user))
        if username in home_shard.users_folder:
            del home_shard.users_folder[username]
        return user

    # TODO: This is probably wrong. creator is generally an entity, this
    # breaks many expectations
    creator = SYSTEM_USER_NAME

    __parent__ = None

    # % is illegal because we sometimes have to
    # URL encode an @ to %40. Comma we reserve as a separator.
    # : and - are used in NTIIDs.
    # NOTE: This is prohibiting Unicode characters
    # NOTE: This has bad effects on FriendsLists since right now they are entities
    # prohibit whitespace and punctuation not needed/allowed in emails
    ALLOWED_USERNAME_CHARS = string.letters + string.digits + '-+.@_'

    def __init__(self, username, parent=None):
        super(Entity, self).__init__()
        __traceback_info__ = username, parent
        if not username or not username.strip():
            # Throw a three-arg version, similar to what a Field would do
            raise UsernameCannotBeBlank(username)

        username = unicode(username)
        for c in username:
            if c not in self.ALLOWED_USERNAME_CHARS:
                raise UsernameContainsIllegalChar(username, self.ALLOWED_USERNAME_CHARS)

        # NOTE: Although we could look for the most derived IEntity self implements
        # and validate against that schema we don't necessarily want to do so
        # at this time since there are so many extent types of IEntity and
        # we haven't enforced constraints like this before. This needs to be
        # cleaned up
        IEntity['username'].bind(self).validate(username)
        self.username = username

        # Entities, and in particular Principals, have a created time,
        # and their last modified date is initialized to this created
        # time...this implies there are never temporary objects of this type
        # and that this type represents a fully formed object after
        # construction
        self.createdTime = self.updateLastMod()

        if parent is not None:
            # If we pre-set this, then the ObjectAdded event doesn't
            # fire (the ObjectCreatedEvent does). On the other hand, we can't
            # add anything to friendsLists if an intid utility is installed
            # if we don't have a parent (and thus cannot be adapted to
            # IKeyReference).
            self.__parent__ = parent

    def _get__name__(self):
        return self.username

    def _set__name__(self, new_name):
        if new_name:
            # Deleting from a container wants to remove our name.
            # We cannot allow that.
            self.username = new_name
    __name__ = property(_get__name__, _set__name__)

    def __repr__(self):
        try:
            return '%s(%s)' % (self.__class__.__name__, self.username)
        except (ConnectionStateError, AttributeError):
            # This most commonly (only?) comes up in unit tests when nose defers logging of an
            # error until after the transaction has exited. There will
            # be other log messages about trying to load state when connection is closed,
            # so we don't need to try to log it as well
            return object.__repr__(self)

    def __str__(self):
        try:
            return self.username
        except ConnectionStateError:
            return object.__str__(self)

    __unicode__ = __str__

    @property
    def id(self):
        """
        Our ID is a synonym for our username
        """
        return self.username

    # Externalization

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        # Notify we're about to update
        if getattr(self, '_p_jar', None):
            do_notify(WillUpdateEntityEvent(self, parsed))

        # Profile info
        profile_iface = IUserProfileSchemaProvider(self).getSchema()
        profile = profile_iface(self)
        # Cause certain fields to be effectively read-only once they are
        # set. At this time, we cannot update the alias or realname fields once created; we assume
        # them to be immutable. There are some few, one-time-only scenarios where we allow updates,
        # usually when our interface has changed
        immutably_named = IImmutableFriendlyNamed.providedBy(self)
        profile_update = IRequireProfileUpdate.providedBy(self)
        if immutably_named:
            if profile.alias and parsed.get('alias'):
                parsed.pop('alias')
            if profile.realname and parsed.get('realname') and not profile_update:
                parsed.pop('realname')

        # Clients may be sending strings; map those to modeled-content.
        about = parsed.get('about')
        if about and isinstance(about, string_types):
            about = [about, ]
            parsed['about'] = about

        # Only validate it though, if we are not saved and not forcing a profile
        # update and we are not disabling it (password reset). Once we are saved,
        # presumably with a valid profile, then if the profile changes and we are
        # missing (new) fields, we cannot necessarily expect to have them filled in.
        validate =     (profile_update or not self._p_mtime) \
                   and not IDoNotValidateProfile.providedBy(self)
        __traceback_info__ = profile_iface, profile_update, validate
        io = InterfaceObjectIO(profile, profile_iface,
                               validate_after_update=validate)
        updated = io.updateFromExternalObject(parsed, *args, **kwargs)
        notify_modified(profile, parsed)
        if profile_update and not IDoNotValidateProfile.providedBy(self):
            # If we got here, then we got the data to validly update our profile,
            # so we can stop providing the update interface
            interface.noLongerProvides(self, IRequireProfileUpdate)

        return updated

    # Comparisons and Hashing

    @CachedProperty
    def _lower_username(self):
        return self.username.lower() if self.username else None

    def __eq__(self, other):
        try:
            return other is self or self._lower_username == other._lower_username
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return self._lower_username < other._lower_username
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return self._lower_username.__hash__()


class _NoOpCm(object):

    def __enter__(self):
        pass

    def __exit__(self, t, v, tb):
        pass
NOOPCM = _NoOpCm()
