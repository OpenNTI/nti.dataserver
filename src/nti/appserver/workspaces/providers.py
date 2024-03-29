#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.location.interfaces import ILocation

from zope.location.location import Location

from nti.appserver import VIEW_ADMINS

from nti.appserver._util import link_belongs_to_user

from nti.appserver.workspaces import IGlobalWorkspaceLinkProvider

from nti.appserver.workspaces.interfaces import IUserWorkspaceLinkProvider

from nti.dataserver.authorization import is_admin

from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUser

from nti.links.links import Link

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IUserWorkspaceLinkProvider)
class _SearchLinksProvider(object):

    def __init__(self, user):
        self.user = user

    def links(self, unused_workspace):
        # Note that we are providing a complete link with a target
        # that is a string and also the name of the link. This is
        # a bit wonky and cooperates with how the CollectionSummaryExternalizer
        # wants to deal with links
        search_parent = Location()
        search_parent.__name__ = 'Search'
        search_parent.__parent__ = self.user
        result = [Link('RecursiveUserGeneratedData', rel='UGDSearch'),
                  Link('UnifiedSearch', rel='UnifiedSearch')]
        for lnk in result:
            lnk.__name__ = lnk.target
            lnk.__parent__ = search_parent
            interface.alsoProvides(lnk, ILocation)
        return result


@component.adapter(IUser)
@interface.implementer(IUserWorkspaceLinkProvider)
class _ResolveMeLinkProvider(object):

    def __init__(self, user):
        self.user = user

    def links(self, unused_workspace):
        user = self.user
        resolve_me_link = Link(user, rel="ResolveSelf", method='GET')
        link_belongs_to_user(resolve_me_link, user)
        return [resolve_me_link]


@component.adapter(IUser)
@interface.implementer(IGlobalWorkspaceLinkProvider)
class _AdminsLinkProvider(object):

    def __init__(self, user):
        self.user = user

    def links(self, unused_workspace):
        if is_admin(self.user):
            ds2 = find_interface(self.user, IDataserverFolder)
            link = Link(ds2, rel=VIEW_ADMINS, method='GET',
                        elements=(VIEW_ADMINS,))
            return [link]
        return ()
