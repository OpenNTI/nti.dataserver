#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces related to link providers.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider


class IDeletableLinkProvider(IAuthenticatedUserLinkProvider):
    """
    A link provider representing state. The links are only provided
    when the state says to; sending an HTTP DELETE request changes
    the state such that the link should no longer be provided.
    """

    def delete_link(link_name):
        """
        Stop providing the particular named link.

        :param unicode link_name: The link name.
        :return: A truthy value that will be true if the link
                existed and was discarded or false of the link didn't exist.
        """


class IFlagLinkEvent(IObjectEvent):
    """
    A flag link has changed. The object will be the user.
    """

    link_name = interface.Attribute("The name of the link that was changed.")


class IFlagLinkAddedEvent(IFlagLinkEvent):
    """
    A flag link was added.
    """


class IFlagLinkRemovedEvent(IFlagLinkEvent):
    """
    A flag link was removed.
    """


@interface.implementer(IFlagLinkEvent)
class FlagLinkEvent(ObjectEvent):

    def __init__(self, obj, link_name):
        super(FlagLinkEvent, self).__init__(obj)
        self.link_name = link_name


@interface.implementer(IFlagLinkAddedEvent)
class FlagLinkAddedEvent(FlagLinkEvent):
    pass


@interface.implementer(IFlagLinkRemovedEvent)
class FlagLinkRemovedEvent(FlagLinkEvent):
    pass
