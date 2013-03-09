#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to link providers.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import functools

from zope import interface

import zope.configuration.fields
from zope.component.zcml import subscriber

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.dataserver.interfaces import IUser
from pyramid.interfaces import IRequest

from nti.utils import schema

from .link_provider import LinkProvider, ConditionalLinkProvider

class INamedLinkDirective(interface.Interface):
	"""
	Register a named link provider.
	"""

	name = zope.configuration.fields.PythonIdentifier(
		title=_("The name of the link."),
		required=True,
		)

	minGeneration = zope.configuration.fields.TextLine(
		title=_("If given, the minimum required value users must have."),
		required=False )

	url = schema.HTTPURL(
		title=_("A URL to redirect to on GET"),
		required=False )

	for_ = zope.configuration.fields.GlobalInterface(
		title="The subtype of user to apply this to",
		required=False,
		default=IUser )

def registerNamedLink( _context, name, minGeneration=None, url=None, for_=IUser ):
	if minGeneration:
		factory = functools.partial( ConditionalLinkProvider, name=name, minGeneration=minGeneration, url=url )
	else:
		factory = functools.partial( LinkProvider, name=name, url=url )
	subscriber( _context, for_=(for_, IRequest), factory=factory, provides=IAuthenticatedUserLinkProvider )
