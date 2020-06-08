#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Notable data interfaces.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.base.interfaces import IIterable

from nti.schema.field import Number

# pylint:disable=I0011,E0213,E0211


class IUserNotableData(IIterable):
    """
    An object, typically registered as an adapter on the user,
    that can find the notable data for that user and answer
    other questions about it.

    Notable objects include:

    * Direct replies to :class:`.IThreadable` objects I created;

    * Top-level content objects (e.g., notes) directly shared to me;

    * Blog-entries shared directly to me;

    * Top-level objects created by certain people (people that are returned
            from subscription adapters to :class:`.IUserPresentationPriorityCreators`);

    * Top-level comments in blog entries I create;

    * Top-level comments in forum discussions (topics) I create;

    * Top-level comments or topics shared to my groups (DFLTopics).

    * Circled events;

    Excluded objects include:

    * Those objects (or descendants of those objects, in some cases)
      specifically marked non-notable;

    * In the future, muted conversations may also be excluded;

    Iterating across this object iterates the notable objects that are
    safely viewable (pass permission checks) by the user.

    In addition to the above noted objects, if the user is adaptable to
    :class:`IUserNotableDataStorage`, then objects found in that interface
    will be added to the set of notable data when this object is iterated.
    """

    def __len__():
        """
        The length of this object is the number of notable objects that can be viewed.
        """

    def __nonzero__():
        """
        The boolean value of this object is whether any notable objects exist
        """

    def get_notable_intids(min_created_time=None,
                           max_created_time=None,
                           include_mentions=True):
        """
        Return a :mod:`BTrees` integer set containing the notable intids for the user.

        :keyword min_created_time: If set to a timestamp, then only intids of objects
                created after that time (inclusive) will be returned.
        :keyword max_created_time: If set to a timestamp, then only intids of objects
                created before that time (inclusive) will be returned.
        """

    def sort_notable_intids(notable_intids,
                            field_name='createdTime',
                            limit=None,
                            reverse=False,
                            reify=False):
        """
        Given (a possible subset of) the intids previously identified as notable
        by this object, sort them according to `field_name` order.

        :keyword createdTime: Defaulting to `createdTime`, this is the field on which to sort.
        :keyword reify: If true, then the return value will be a list-like sequence supporting
                indexing and having a length. If `False` (the default) the return value may
                be a generator or index.
        :return: An iterable or list-like sequence containing intids.
        """

    def iter_notable_intids(notable_intids):
        """
        Return an iterable over the objects represented by the intids
        previously returned and possibly sorted by this object.
        """

    def is_object_notable(maybe_notable):
        """
        Given an object, check to see if it should be considered part of the
        notable set for this user, returning a truthy-value.
        """

    def object_is_not_notable(maybe_notable):
        """"
        Given some object, attempt to record that whatever its notability
        status is it should no longer be considered notable. For example,
        to declare that comments in a created topic should not be notable,
        pass the topic.
        """

    # TODO: Arguably this should be a separate interface we adapt to or extend?
    lastViewed = Number(title=u"The timestamp the user last viewed this data",
                        description=u"This is not set implicitly, but should be set explicitly "
                        u"by user action. 0 if never set.",
                        required=True,
                        default=0)


class IUserNotableProvider(interface.Interface):
    """
    Registered as a subscription adapter to a (subclass of)
    :class:`IUser` and the request. Used to provide a filtered
    set of objects for notables for a certain user.
    """

    def get_notable_intids():
        """
        Return a :mod:`BTrees` integer set containing the notable intids for the user.
        """


class IUserNotableSharedWithIDProvider(interface.Interface):
    """
    Registered as a subscription adapter to a (subclass of)
    :class:`IUser` and the request. Used to provide a set of shared with
    NTIIDs to query for notables.
    """

    def get_shared_with_ids():
        """
        Return a set of ids to query for sharedWith content.
        """


class IUserNotableDataStorage(interface.Interface):
    """
    An implementation helper for objects which otherwise do not
    have defined storage or which somehow modify the rules for notable
    data. Objects and intids stored by this interface are defined to be notable,
    but they may be subject to permission checks or exclusion.

    As an implementation helper, this object knows how to work across two
    dimensions:

    * safe vs not safe: is the object or intid defined to be viewable by the
            user who we adapted from?
    * owned vs unowned: Is the object owned (will or does) already have a
            __parent__ and intid assigned my someone else, or should we
            take care of broadcasting the created and added events, by
            storing the object in an internal container?

    Again as a provisional implementation helper, the query API is private.
    """

    # Note no provision for removing yet, can add that when
    # needed

    def store_intid(intid, safe=False):
        """
        Mark the (object referenced by the) given intid to be notable
        data. These objects should generally not go away.
        """

    def store_object(obj, safe=False, take_ownership=False):
        """
        Mark the object itself as notable, possibly taking ownership
        and broadcasting created and added events. If, after that's done if needed,
        the object does not have an intid, an exception is raised.
        """
