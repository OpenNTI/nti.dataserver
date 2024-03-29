#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.threadlocal import get_current_request

from zc.displayname.interfaces import IDisplayNameGenerator

from ZODB.interfaces import IConnection

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from nti.app.users.model import ContextLastSeenBTreeContainer

from nti.appserver.interfaces import IEditLinkMaker

from nti.appserver.pyramid_renderers_edit_link_decorator import DefaultEditLinkMaker

from nti.coremetadata.interfaces import IContextLastSeenContainer

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IDisplayNameAdapter

from nti.traversal.traversal import find_interface

CONTEXT_LASTSEEN_ANNOTATION_KEY = 'nti.coremetadata.interfaces.IContextLastSeenContainer'

logger = __import__('logging').getLogger(__name__)

# index


class _Displayname(object):

    __slots__ = ('displayname',)

    def __init__(self, name):
        self.displayname = name


def _default_displayname(user):
    name = IFriendlyNamed(user)
    return name.alias or name.realname or user.username


@component.adapter(IUser)
@interface.implementer(IDisplayNameAdapter)
def _user_to_displayname(context):
    generator = component.queryMultiAdapter((context, get_current_request()),
                                            IDisplayNameGenerator)
    name = generator() if generator is not None else None
    name = name or _default_displayname(context)
    return _Displayname(name)


# context last seen


def context_lastseen_factory(user, create=True):
    result = None
    annotations = IAnnotations(user)
    KEY = CONTEXT_LASTSEEN_ANNOTATION_KEY
    try:
        result = annotations[KEY]
    except KeyError:
        if create:
            result = ContextLastSeenBTreeContainer()
            annotations[KEY] = result
            result.__name__ = KEY
            result.__parent__ = user
            # pylint: disable=too-many-function-args
            IConnection(user).add(result)
    return result


@interface.implementer(IUser)
@component.adapter(IContextLastSeenContainer)
def _context_lastseen_to_user(context):
    return find_interface(context, IUser)


@interface.implementer(IEditLinkMaker)
@component.adapter(IDynamicSharingTargetFriendsList)
class _DFLEditLinkMaker(DefaultEditLinkMaker):

    def make(self, context, request=None, allow_traversable_paths=True, link_method=None):
        if not context.Locked:
            return super(_DFLEditLinkMaker, self).make(context, request,
                                                       allow_traversable_paths,
                                                       link_method)
