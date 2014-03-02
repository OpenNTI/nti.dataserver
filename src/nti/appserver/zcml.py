#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
import zope.configuration.fields
from zope.component.zcml import utility

from .interfaces import ILogonWhitelist

class ILogonWhitelistDirective(interface.Interface):
	"""
	A specific list of named users are allowed to login.
	"""

	entities = zope.configuration.fields.Tokens(
		title="The global usernames allowed to logon",
		required=True,
		value_type=zope.configuration.fields.TextLine(title="The entity identifier."),
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
