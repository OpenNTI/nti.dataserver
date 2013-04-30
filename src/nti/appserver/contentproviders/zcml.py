#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to content providers.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface
from zope.contentprovider.interfaces import IContentProvider

import zope.configuration.fields
from zope.component.zcml import adapter

from nti.utils import schema

from .pyramid import PyramidRendererContentProviderFactory

class IPyramidRendererDirective(interface.Interface):
	"""
	Register a pyramid renderer template as a content provider.
	"""

	template = schema.ValidTextLine(
		title=_("The name of the template."),
		required=True,
		min_length=1 )

	name = schema.ValidTextLine(
		title=_("The name of the content provider."),
		required=False,
		min_length=1 )

	for_ = zope.configuration.fields.Tokens(
		title=_("Specifications to be adapted"),
		description=_("This should be a list of interfaces or classes"),
		required=False,
		value_type=zope.configuration.fields.GlobalObject( missing_value=object() )
        )


def registerPyramidRenderer( _context, template, name='', for_=None ):

	factory = PyramidRendererContentProviderFactory( template )

	adapter( _context, (factory,), provides=IContentProvider, for_=for_, name=name )
