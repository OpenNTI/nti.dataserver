#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to link providers.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface

from zope.component.zcml import subscriber

from zope.configuration.exceptions import ConfigurationError

from zope.configuration.fields import GlobalObject
from zope.configuration.fields import GlobalInterface
from zope.configuration.fields import PythonIdentifier

from zope.mimetype.interfaces import mimeTypeConstraint

from zope.schema import TextLine

from pyramid.interfaces import IRequest

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.appserver.link_providers.link_provider import LinkProvider
from nti.appserver.link_providers.link_provider import GenerationalLinkProvider
from nti.appserver.link_providers.link_provider import NoUserLinkProvider

from nti.base._compat import text_

from nti.dataserver.interfaces import IMissingUser
from nti.dataserver.interfaces import IUser

from nti.schema.field import ValidTextLine

class _ILinkDirective(interface.Interface):
    
    name = ValidTextLine(
        title=u"The name of the link.",
        description=u"This literal value will be used as the relationship type of the link. You must provide either this or ``named``",
        required=False,
        min_length=1)

    named = GlobalObject(
        title=u"Path to string constant giving the name.",
        description=u"You must give this or ``name``.",
        required=False,
        value_type=name)

    mimeType = ValidTextLine(
        title=u"The mime type expected to be returned by the link",
        constraint=mimeTypeConstraint,
        required=False)

class IMissingUserLinkDirective(_ILinkDirective):
    """
    Register a named link provider for missing users (unauthenticated)
    """
    
    url = ValidTextLine(  # Because we want to allow putting in just the path portion of the URL allowing for site-relative urls. But those aren't valid by themselves.
        title=u"A URI to redirect to on GET",
        description=u"NOTE: This is not enforced to be a complete, valid URL/URI. You are responsible for that.",
        required=True)

class IUserLinkDirective(_ILinkDirective):
    """
    Register a named link provider for a user.
    """

    minGeneration = TextLine(
        title=u"If given, the minimum required value users must have.",
        description=u"""A text string that should be monotonically increasing because it is lexographically compared. For dates, use YYYYMMDD. Mutually exclusive with ``field``.""",
        required=False)

    url = ValidTextLine(  # Because we want to allow putting in just the path portion of the URL allowing for site-relative urls. But those aren't valid by themselves.
        title=u"A URI to redirect to on GET",
        description=u"NOTE: This is not enforced to be a complete, valid URL/URI. You are responsible for that. Mutually exclusive with ``field``",
        required=False)

    field = PythonIdentifier(
        title=u"A field on the user that this will link to, using the ++fields namespace",
        description=u"Mutually exclusive with ``url`` and ``minGeneration``",
        required=False)

    view_named = GlobalObject(
        title=u"Path to string constant giving the name of a view.",
        description=u"If given, this will be used as the destination of the link, thus mutually exclusive with ``field``, ``minGeneration`` and ``url``",
        required=False,
        value_type=_ILinkDirective['name'])

    for_ = GlobalInterface(
        title=u"The subtype of user to apply this to",
        required=False,
        default=IUser)

def registerMissingUserLink(_context,
                            name=None,
                            named=None,
                            url=None,
                            mimeType=None):

    if name and named:
        raise ConfigurationError("Pick either name or named, not both")
    if named:
        name = named
    if not name:
        raise ConfigurationError("Specify either name or named")

    kwargs = dict(name=text_(name),
                  url=text_(url),
                  mime_type=text_(mimeType))

    factory = functools.partial(NoUserLinkProvider, **kwargs)
    subscriber(_context, for_=(IRequest,),
               factory=factory, provides=IUnauthenticatedUserLinkProvider)

    
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
        # because going to a field is handled by its own views
        raise ConfigurationError("Pick either field or minGeneration, not both")

    if view_named and (field or minGeneration or url):
        raise ConfigurationError("Pick one of view_named, field, minGeneration, or url")

    kwargs = dict(name=text_(name),
                  url=text_(url),
                  view_named=text_(view_named),
                  field=text_(field),
                  mime_type=text_(mimeType))

    if minGeneration:
        factory = functools.partial(GenerationalLinkProvider,
                                    minGeneration=minGeneration, **kwargs)
    else:
        factory = functools.partial(LinkProvider, **kwargs)
    subscriber(_context, for_=(for_, IRequest),
               factory=factory, provides=IAuthenticatedUserLinkProvider)
