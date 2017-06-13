#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of
:class:`nti.appserver.IAuthenticatedUserLinkProvider` providing a
collection of links used as flags.

In general, links will be added to the user through the functions of
this module. There is no defined GET behaviour for the flag links,
but the client is expected to notice their existence and take appropriate
action. When that action is complete, a DELETE to that
same URL will remove the link (if it is not removed implicitly by
some other action; this could be done with one of the workflow
packages like ``hurry.workflow`` but for now our needs are simple
enough that they are overkill.)

Delete behaivour is provided automatically.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.event import notify

from zope.annotation.interfaces import IAnnotations

from pyramid.interfaces import IRequest

from BTrees.OOBTree import OOTreeSet

from nti.appserver.link_providers.interfaces import FlagLinkAddedEvent
from nti.appserver.link_providers.interfaces import FlagLinkRemovedEvent
from nti.appserver.link_providers.interfaces import IDeletableLinkProvider

from nti.appserver.link_providers.link_provider import LinkProvider

from nti.common import sets

from nti.dataserver.interfaces import IUser

# We store links in an OOTreeSet annotation on the User object
_PKG_ANNOTATION_KEY = 'nti.appserver.user_link_provider'
_LINK_ANNOTATION_KEY = _PKG_ANNOTATION_KEY + '.LinkAnnotation'  # BWC


def add_link(user, link_name):
    """
    Add the given link name to the user.

    :param user: An annotatable user.
    :param unicode link_name: The link name.
    """
    the_set = IAnnotations(user).get(_LINK_ANNOTATION_KEY)
    if the_set is None:
        the_set = OOTreeSet()
        IAnnotations(user)[_LINK_ANNOTATION_KEY] = the_set
    if link_name not in the_set:
        notify(FlagLinkAddedEvent(user, link_name))
    the_set.add(link_name)


def has_link(user, link_name):
    """
    Primarily for testing, answer whether the user is known to
    have the given link.

    :param user: An annotatable user.
    :param unicode link_name: The link name.
    """

    the_set = IAnnotations(user).get(_LINK_ANNOTATION_KEY, ())
    return link_name in the_set


def delete_link(user, link_name):
    """
    Ensure the given user does not have a link with the
    given name.

    :param user: An annotatable user.
    :param unicode link_name: The link name.
    :return: A truthy value that will be true if the link
            existed and was discarded or false of the link didn't exist.
    """
    the_set = IAnnotations(user).get(_LINK_ANNOTATION_KEY)
    if the_set is None:
        return
    result = sets.discard_p(the_set, link_name)
    if result:
        notify(FlagLinkRemovedEvent(user, link_name))
    return result
_delete_link = delete_link


@component.adapter(IUser, IRequest)
@interface.implementer(IDeletableLinkProvider)
class FlagLinkProvider(LinkProvider):

    def get_links(self):
        the_set = IAnnotations(self.user).get(_LINK_ANNOTATION_KEY, ())
        return [self._make_link_with_rel(link_name) for link_name in the_set]

    def delete_link(self, link_name):
        return _delete_link(self.user, link_name)
