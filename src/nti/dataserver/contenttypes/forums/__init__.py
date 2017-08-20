#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Package containing forum support.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import component

from zope.cachedescriptors.property import CachedProperty as _CachedProperty

from zope.intid.interfaces import IIntIds

from Acquisition import aq_parent

from nti.dataserver.contenttypes.forums.interfaces import IUseOIDForNTIID

from nti.dataserver.interfaces import IPrincipal

from nti.externalization.oids import to_external_ntiid_oid

from nti.ntiids.ntiids import DATE as _NTIID_DATE
from nti.ntiids.ntiids import make_ntiid as _make_ntiid

from nti.property.property import alias as _alias

from nti.traversal.traversal import find_interface


class _AcquiredSharingTargetsProperty(object):

    def __get__(self, instance, unused_klass):
        if instance is None:
            return self
        # NOTE: This only works if __parent__ is already set.
        # It fails otherwise
        return getattr(aq_parent(instance), 'sharingTargets', ())

    def __set__(self, unused_instance, unused_value):
        return  # Ignored


class _CreatedNamedNTIIDMixin(object):
    """
    Mix this in to get NTIIDs based on the creator and name.
    You must define the ``ntiid_type``.

    .. py:attribute:: _ntiid_type
            The string constant for the type of the NTIID.

    .. py:attribute:: _ntiid_include_parent_name
            If True (not the default) the ``__name__`` of our ``__parent__``
            object is included in the specific part, preceding our name
            and separated by a dot. Use this if our name is only unique within
            our parent. (We choose a dot because it is not used by :func:`.make_specific_safe`.)

    """

    creator = None
    __name__ = None

    _ntiid_type = None
    _ntiid_include_parent_name = False

    @property
    def _ntiid_mask_creator(self):
        return True

    @property
    def _ntiid_creator_username(self):
        # TODO We could use username here if we have it, falling back to
        # using the principal id.
        return IPrincipal(self.creator).id if self.creator else None

    @property
    def _ntiid_specific_part(self):
        if not self._ntiid_include_parent_name:
            return self.__name__
        try:
            if self.__parent__.__name__:
                return self.__parent__.__name__ + '.' + self.__name__
            else:
                return None
        except AttributeError:  # Not ready yet
            return None

    @_CachedProperty('_ntiid_creator_username', '_ntiid_specific_part')
    def NTIID(self):
        """
        NTIID is defined only after the _ntiid_creator_username is
        set; until then it is none. We cache based on this value and
        our specific part (which includes our __name__)
        """
        if find_interface(self, IUseOIDForNTIID, strict=False) is not None:
            return to_external_ntiid_oid(self, mask_creator=self._ntiid_mask_creator)

        creator_name = self._ntiid_creator_username
        if creator_name:
            return _make_ntiid(date=_NTIID_DATE,
                               provider=creator_name,
                               nttype=self._ntiid_type,
                               specific=self._ntiid_specific_part)


class _CreatedIntIdNTIIDMixin(_CreatedNamedNTIIDMixin):
    """
    Mix this in to get NTIIDs based on the creator and its intid.
    You must define the ``ntiid_type``.
    """

    creator = None
    __name__ = None

    _ntiid_type = None
    _ntiid_include_parent_name = False

    @property
    def _ntiid_creator_username(self):
        intids = component.queryUtility(IIntIds)
        if intids is not None and self.creator:
            return intids.queryId(self.creator)


def _containerIds_from_parent():
    """
    Returns a tuple of properties to assign to id and containerId
    """

    # BWC: Some few objects will have this is their __dict__, but that's OK, it should
    # match what we get anyway (and if it doesn't, its wrong)

    def _get_containerId(self):
        if self.__parent__ is not None:
            try:
                return self.__parent__.NTIID
            except AttributeError:
                # Legacy support: the parent is somehow dorked up. If we have one in
                # our __dict__ still, use it. Otherwise, let the error
                # propagate.
                if 'containerId' in self.__dict__:
                    return self.__dict__['containerId']
                raise

    def _set_containerId(self, cid):
        pass  # ignored

    # Unlike the superclass, we define the nti_interfaces.IContained properties
    # as aliases for the zope.container.IContained values

    return _alias('__name__'), property(_get_containerId, _set_containerId)
