#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,inconsistent-mro

from zope import interface

from nti.appserver.workspaces.interfaces import IWorkspace
from nti.appserver.workspaces.interfaces import IContainerCollection


class ICommunitiesWorkspace(IWorkspace):
    """
    A workspace to provide community management for a user.
    """


class ICommunitiesWorkspaceLinkProvider(interface.Interface):

    def links(workspace):
        """
        return an iterable of community links
        """


class ICommunitiesCollection(IContainerCollection):
    """
    A collection contained within the :class:``ICommunitiesWorkspace``,
    containing communities.
    """


class IJoinedCommunitiesCollection(ICommunitiesCollection):
    """
    A collection contained within the :class:``ICommunitiesWorkspace``,
    containing those communites the user is a member of.
    """


class IAdministeredCommunitiesCollection(ICommunitiesCollection):
    """
    A collection contained within the :class:``ICommunitiesWorkspace``,
    containing those communities user administers.
    """

class IAllCommunitiesCollection(ICommunitiesCollection):
    """
    A collection contained within the :class:``ICommunitiesWorkspace``,
    containing those communities a user may join.
    """
