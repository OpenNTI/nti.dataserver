#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from BTrees.OOBTree import OOBTree

from zope import component
from zope import interface

from zope.location import locate

from zope.preference.interfaces import IDefaultPreferenceProvider
from zope.preference.interfaces import IPreferenceCategory

from zope.preference.preference import PreferenceGroupChecker

from zope.security.checker import defineChecker

from zope.traversing.interfaces import IContainmentRoot

from zope.preference.default import DefaultPreferenceProvider

from nti.dataserver.preference.interfaces import INTIPreferenceGroup

from nti.dataserver.preference.preference import NTIPreferenceGroup

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDefaultPreferenceProvider)
class NTIDefaultPreferenceProvider(DefaultPreferenceProvider):
    """
    Closely matches zope.preference.default.DefaultPreferenceProvider with updated
    references to NTIPreferenceGroups
    """

    def getDefaultPreferenceGroup(self, id=''):
        # match the super class method signature but require id
        if not id:
            raise KeyError(u'ID must be provided.')
        group = component.getUtility(INTIPreferenceGroup, name=id)
        group = group.__bind__(self)
        default = NTIDefaultPreferenceGroup(group, self)
        interface.alsoProvides(default, IContainmentRoot)
        locate(default, self, 'preferences')
        return default


class NTIDefaultPreferenceGroup(NTIPreferenceGroup):
    """A preference group representing the site-wide default values.
    The implementation closely resembles zope.preference.default.DefaultPreferenceGroup
    with updated references to NTIPreferenceGroups"""

    def __init__(self, group, provider):
        self.provider = provider
        super(NTIDefaultPreferenceGroup, self).__init__(
            group.__id__, group.__annotation_factory__, group.__schema__,
            group.__title__, group.__description__)

        # Make sure that we also mark the default group as category if the
        # actual group is one; this is important for the UI.
        if IPreferenceCategory.providedBy(group):
            interface.alsoProvides(self, IPreferenceCategory)

    def get(self, key, default=None):
        group = super(NTIDefaultPreferenceGroup, self).get(key, default)
        if group is default:
            return default
        return NTIDefaultPreferenceGroup(group, self.provider).__bind__(self)

    def items(self):
        return [
            (id, NTIDefaultPreferenceGroup(group, self.provider).__bind__(self))
            for id, group in super(NTIDefaultPreferenceGroup, self).items()]

    def __getattr__(self, key):
        # Try to find a sub-group of the given id
        group = self.get(key)
        if group is not None:
            return group

        # Try to find a preference of the given name
        if self.__schema__ and key in self.__schema__:
            marker = object()
            value = self.data.get(key, marker)
            if value is not marker:
                return value

            # There is currently no local entry, so let's go to the next
            # provider and lookup the group and value there.
            nextProvider = component.queryNextUtility(
                self.provider, IDefaultPreferenceProvider)

            # No more providers found, so return the schema's default
            if nextProvider is None:
                return self.__schema__[key].default

            nextGroup = nextProvider.getDefaultPreferenceGroup(self.__id__)
            return getattr(nextGroup, key, self.__schema__[key].default)

        # Nothing found, raise an attribute error
        raise AttributeError("'%s' is not a preference or sub-group." % key)

    @property
    def data(self):
        if self.__id__ not in self.provider.data:
            self.provider.data[self.__id__] = OOBTree()

        return self.provider.data[self.__id__]


defineChecker(NTIDefaultPreferenceGroup, PreferenceGroupChecker)
