#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters and utilities for working with avatar URLs.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from . import interfaces

from nti.utils import create_gravatar_url


@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IAvatarURL)
def AvatarURLFactory(entity):
	"""
	For legacy reasons, this factory first checks for the presence of an avatar URL
	"""
	from IPython.core.debugger import Tracer; Tracer()() ## DEBUG ##

	# Something explicitly set, historical
	if getattr( entity, '_avatarURL', None ):
		return entity

	return component.queryAdapter( entity, interfaces.IAvatarURL, name="generated" )

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IAvatarURL)
class GravatarComputedAvatarURL(object):

	defaultGravatarType = 'mm'

	def __init__( self, context ):
		self.avatarURL = create_gravatar_url( context.username,
											  getattr( context, 'defaultGravatarType', self.defaultGravatarType ) )
