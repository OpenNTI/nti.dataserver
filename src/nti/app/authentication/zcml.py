#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
..  $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.component.zcml import utility

from zope.configuration.fields import Tokens
from zope.configuration.fields import TextLine

from nti.app.authentication.interfaces import ILogonWhitelist
from nti.app.authentication.interfaces import ISiteLogonWhitelist

logger = __import__('logging').getLogger(__name__)


class ILogonWhitelistDirective(interface.Interface):
    """
    A specific list of named users are allowed to login.
    """

    entities = Tokens(
        title=u"The global usernames allowed to logon",
        required=True,
        value_type=TextLine(title=u"The entity identifier."),
    )


def registerLogonWhitelist(_context, entities):
    """
    Register a whitelist utility.
    """

    if not entities:
        logger.warning("No one is allowed to logon")

    whitelist = frozenset(entities)
    if len(whitelist) != len(entities):
        logger.warning("Duplicate entities in list")

    utility(_context, provides=ILogonWhitelist, component=whitelist)


class ISiteLogonWhitelistDirective(interface.Interface):
    """
    A specific list of named sites users are allowed to login.
    """

    sites = Tokens(
        title=u"The global sites users are allowed to logon",
        required=True,
        value_type=TextLine(title=u"The site identifier."),
    )


def registerSiteLogonWhitelist(_context, sites):
    """
    Register a site whitelist utility.
    """

    if not sites:
        logger.warning("No one is allowed to logon")

    whitelist = frozenset(sites)
    if len(whitelist) != len(sites):
        logger.warning("Duplicate sites in list")

    utility(_context, provides=ISiteLogonWhitelist, component=whitelist)
