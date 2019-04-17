#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions and architecture for general activity streams.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from operator import setitem

from zope import component
from zope import interface

from zope.interface.declarations import ObjectSpecificationDescriptor

from zope.security.interfaces import IPrincipal

from ZODB.POSException import POSError

from nti.dataserver.authorization_acl import ACL

from nti.dataserver.interfaces import SC_SHARED
from nti.dataserver.interfaces import SC_CREATED
from nti.dataserver.interfaces import SC_CIRCLED
from nti.dataserver.interfaces import SC_DELETED
from nti.dataserver.interfaces import SC_MODIFIED
from nti.dataserver.interfaces import SC_CHANGE_TYPE_MAP

from nti.dataserver.interfaces import IContained
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import INeverStoredInSharedStream
from nti.dataserver.interfaces import IUseNTIIDAsExternalUsername

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.externalization import toExternalObject

from nti.externalization.oids import toExternalOID

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.wref.interfaces import IWeakRef

ID = StandardExternalFields.ID
OID = StandardExternalFields.OID
CLASS = StandardExternalFields.CLASS
CREATOR = StandardExternalFields.CREATOR
MIMETYPE = StandardExternalFields.MIMETYPE
LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED


def _weak_ref_to(obj):
    try:
        return IWeakRef(obj)
    except TypeError:
        # For the sake of old tests, we allow things that cannot be weakly
        # ref'd.
        return obj


class _DynamicChangeTypeProvidedBy(ObjectSpecificationDescriptor):

    type_cache = dict()

    def __get__(self, inst, cls):
        result = ObjectSpecificationDescriptor.__get__(self, inst, cls)
        if inst is not None and inst.type in SC_CHANGE_TYPE_MAP:
            inst_type = type(inst)
            try:
                result = self.type_cache[inst_type]
            except KeyError:
                result = result + SC_CHANGE_TYPE_MAP[inst.type]
                self.type_cache[inst_type] = result
        return result


@interface.implementer(IStreamChangeEvent, IZContained)
class Change(PersistentCreatedModDateTrackingObject):
    """
    A change notification. For convenience, it acts like a
    Contained object if the underlying object was Contained.
    It externalizes to include the ChangeType, Creator, and Item.

    Because changes are meant to be part of an ongoing stream of
    activity, which may be cached in many different places that are
    not necessarily planned for or easy to find, these objects only
    keep a weak reference to the modified object. For that same
    reason, they only keep a weak reference to their `creator`
    (which must be set after construction).

    If there is a knows sub-interface for the particular kind of
    change type this object represents, it will provide that interface.
    We do this dynamically to avoid issues if certain change types come
    and go across different sites or configurations.
    """

    mime_type = mimeType = nti_mimetype_with_class('Change')

    parameters = {}  # immutable

    SHARED = SC_SHARED
    CREATED = SC_CREATED
    CIRCLED = SC_CIRCLED
    DELETED = SC_DELETED
    MODIFIED = SC_MODIFIED

    #: If set to `True` (not the default) then when this object
    #: is externalized, the externalizer named "summary" will
    #: be used for the enclosed object.
    useSummaryExternalObject = False

    #: If set to a callable object, then before doing any externalization,
    #: we will call this object with the non-None object we hold,
    #: and externalize the results.
    #: This can be used to do some transformation of the contained object
    #: when it is convenient to hold one thing but externalize another
    #: (e.g., when the external object cannot be persisted.) Note
    #: that if you assign to this property it must be a valid persistent
    #: object, such as a module global.
    externalObjectTransformationHook = None

    # JAM: I'm not quite happy with the above. it's convenient, but is it
    # the best abstraction?
    object_is_shareable = \
        property(lambda self: self.__dict__.get('_v_object_is_shareable', None),
                 lambda self, val: setitem(self.__dict__, str('_v_object_is_shareable'), val))

    # FIXME: So badly wrong at this level
    send_change_notice = \
        property(lambda self: self.__dict__.get('_v_send_change_notice', True),  # default to true
                 lambda self, val: setitem(self.__dict__, str('_v_send_change_notice'), val))

    __name__ = None
    __parent__ = None

    # Notice we do not inherit from ContainedMixin, and we do not implement
    # IContained. We do that conditionally if the object we're wrapping
    # has these things
    id = None
    type = None
    containerId = None

    __providedBy__ = _DynamicChangeTypeProvidedBy()

    def __init__(self, changeType, obj):
        super(Change, self).__init__()
        self.type = changeType
        # We keep a weak reference to the object, but
        # we actually store the container information so that it's
        # useful after the object goes away
        self.objectReference = _weak_ref_to(obj)

        for k in ('id', 'containerId', '__name__', '__parent__'):
            v = getattr(obj, k, None)
            if v is not None:
                setattr(self, str(k), v)  # ensure native string in dict

        if self.id and self.containerId:
            interface.alsoProvides(self, IContained)
        # We don't copy the object's modification date,
        # we have our own
        self.updateLastMod()

    def __copy__(self):
        # The default copy.copy mechanism, which uses the same mechanism
        # as pickle (__reduce__ex__, etc) is not guaranteed to preserve
        # our volatile attributes because we are Persistent and those get
        # dropped from the pickle
        copy = self.__class__.__new__(self.__class__)
        for k, v in self.__dict__.items():
            copy.__dict__[k] = v
        return copy

    def _get_creator(self):
        creator = self.__dict__.get('creator')
        if creator and callable(creator):
            creator = creator()  # unwrap weak refs. Older or test objects may not have weak refs
        return creator

    def _set_creator(self, new_creator):
        if new_creator:
            new_creator = _weak_ref_to(new_creator)
        # ensure native string in dict
        self.__dict__[str('creator')] = new_creator
    creator = property(_get_creator, _set_creator)

    @property
    def object(self):
        """
        Returns the object to which this reference refers,
        or None if the object no longer exists.
        """
        return self.objectReference()

    #: If true (not the default) we will assume the ACL of our contained
    #: object at access time.
    __copy_object_acl__ = False

    def __acl__(self):
        if not self.__copy_object_acl__:
            return ()  # No opinion
        o = self.object
        if o is None:
            return ()  # Gone
        return ACL(o, ())

    def values(self):
        """
        For migration compatibility with :mod:`zope.generations.utility`, this
        method returns the same thing as :meth:`object`.
        """
        yield self.object

    def _get_sharedWith(self):
        sharedWith = self.__dict__.get('sharedWith')
        if not sharedWith:
            sharedWith = getattr(self.object, 'sharedWith', None)
        return sharedWith

    def _set_sharedWith(self, sharedWith):
        if sharedWith:
            self.__dict__[str('sharedWith')] = sharedWith
    sharedWith = property(_get_sharedWith, _set_sharedWith)

    def hasSharedWith(self):
        return 'sharedWith' in self.__dict__

    def isSharedDirectlyWith(self, principal):
        """
        Test if the principal is directly shared with this Change object
        """
        principal = IPrincipal(principal)
        sharedWith = self.__dict__.get('sharedWith') or ()
        return principal.id in sharedWith

    def isSharedIndirectlyWith(self, principal):
        """
        Test if the principal is in the underlying's object sharedWith attribute
        """
        principal = IPrincipal(principal)
        sharedWith = getattr(self.object, 'sharedWith', None) or ()
        return principal.id in sharedWith

    def is_object_shareable(self):
        """
        Returns true if the object is supposed to be copied into local shared data.
        """
        if self.object_is_shareable is not None:
            return self.object_is_shareable

        result = not INeverStoredInSharedStream.providedBy(self.object)
        # We assume this won't change for the lifetime of the object
        self.object_is_shareable = result
        return result

    def __repr__(self):
        try:
            return "%s('%s',%s)" % (self.__class__.__name__, self.type,
                                    self.object.__class__.__name__)
        except (POSError, AttributeError):
            return object.__repr__(self)


@interface.implementer(IExternalObject)
@component.adapter(IStreamChangeEvent)
class _ChangeExternalObject(object):

    def __init__(self, change):
        self.change = change

    def toExternalObject(self, *unused_args, **kwargs):
        kwargs.pop('name', None)
        change = self.change
        wrapping = change.object
        if wrapping is not None and callable(change.externalObjectTransformationHook):
            wrapping = change.externalObjectTransformationHook(wrapping)
        result = LocatedExternalDict()
        result.__parent__ = getattr(wrapping, '__parent__', None) \
                         or getattr(change, '__parent__', None)
        result.__name__ = getattr(wrapping, '__name__', None) \
                       or getattr(change, '__name__', None)
        result[CLASS] = 'Change'
        result[MIMETYPE] = Change.mimeType
        # set creator
        result[CREATOR] = None
        change_creator = change.creator  # set creator
        if change_creator:
            if IUseNTIIDAsExternalUsername.providedBy(change_creator):
                result[CREATOR] = change_creator.NTIID
            elif hasattr(change_creator, 'username'):
                result[CREATOR] = change_creator.username
            else:
                result[CREATOR] = change_creator
        result['ChangeType'] = change.type
        result[LAST_MODIFIED] = change.lastModified
        # set ids
        result[ID] = change.id or None
        # OIDs must be unique
        result[OID] = toExternalOID(change)
        result['Item'] = None
        if wrapping is not None:
            name = ('summary' if change.useSummaryExternalObject else '')
            result['Item'] = toExternalObject(wrapping, name=name, **kwargs)
        return result
