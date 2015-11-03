#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to link providers.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface

import zope.configuration.fields

from zope.component.zcml import subscriber
from zope.mimetype.interfaces import mimeTypeConstraint
from zope.configuration.exceptions import ConfigurationError

from pyramid.interfaces import IRequest

from nti.dataserver.interfaces import IUser
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider

from nti.schema.field import ValidTextLine

from .link_provider import LinkProvider, GenerationalLinkProvider

class IUserLinkDirective(interface.Interface):
	"""
	Register a named link provider.
	"""

	name = ValidTextLine(
		title="The name of the link.",
		description="This literal value will be used as the relationship type of the link. You must provide either this or ``named``",
		required=False,
		min_length=1)

	named = zope.configuration.fields.GlobalObject(
		title="Path to string constant giving the name.",
		description="You must give this or ``name``.",
		required=False,
		value_type=name)

	minGeneration = zope.configuration.fields.TextLine(
		title="If given, the minimum required value users must have.",
		description="""A text string that should be monotonically increasing because it is lexographically compared. For dates, use YYYYMMDD. Mutually exclusive with ``field``.""",
		required=False)

	url = ValidTextLine(# Because we want to allow putting in just the path portion of the URL allowing for site-relative urls. But those aren't valid by themselves.
		title="A URI to redirect to on GET",
		description="NOTE: This is not enforced to be a complete, valid URL/URI. You are responsible for that. Mutually exclusive with ``field``",
		required=False)

	field = zope.configuration.fields.PythonIdentifier(
		title="A field on the user that this will link to, using the ++fields namespace",
		description="Mutually exclusive with ``url`` and ``minGeneration``",
		required=False)

	view_named = zope.configuration.fields.GlobalObject(
		title="Path to string constant giving the name of a view.",
		description="If given, this will be used as the destination of the link, thus mutually exclusive with ``field``, ``minGeneration`` and ``url``",
		required=False,
		value_type=name)

	mimeType = ValidTextLine(
		title="The mime type expected to be returned by the link",
		constraint=mimeTypeConstraint,
		required=False)

	for_ = zope.configuration.fields.GlobalInterface(
		title="The subtype of user to apply this to",
		required=False,
		default=IUser)

def registerUserLink(_context,
					 name=None,
					 named=None,
					 minGeneration=None,
					 url=None,
					 field=None,
					 view_named=None,
					 mimeType=None,
					 for_=IUser):

	if name and named:
		raise ConfigurationError("Pick either name or named, not both")
	if named:
		name = named
	if not name:
		raise ConfigurationError("Specify either name or named")

	if not for_ or not for_.isOrExtends(IUser):
		raise ConfigurationError("For must be a user type")

	if field and url:
		raise ConfigurationError("Pick either field or url, not both")

	if field and minGeneration:
		raise ConfigurationError("Pick either field or minGeneration, not both")  # because going to a field is handled by its own views

	if view_named and (field or minGeneration or url):
		raise ConfigurationError("Pick one of view_named, field, minGeneration, or url")

	kwargs = dict(name=name, url=url, view_named=view_named, field=field, mime_type=mimeType)

	if minGeneration:
		factory = functools.partial(GenerationalLinkProvider, minGeneration=minGeneration, **kwargs)
	else:
		factory = functools.partial(LinkProvider, **kwargs)
	subscriber(_context, for_=(for_, IRequest), factory=factory, provides=IAuthenticatedUserLinkProvider)
