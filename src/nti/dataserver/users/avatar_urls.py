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
	# Something explicitly set, historical
	if getattr( entity, '_avatarURL', None ):
		return _FixedAvatarWrapper( entity )

	return component.queryAdapter( entity, interfaces.IAvatarURL, name="generated" )

@interface.implementer(interfaces.IAvatarURL)
class _FixedAvatarWrapper(object):

	def __init__( self, context ):
		self.avatarURL = getattr( context, '_avatarURL' )

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IAvatarURL)
class GravatarComputedAvatarURL(object):

	defaultGravatarType = 'mm'

	def __init__( self, context ):

		email = context.username
		try:
			profile = interfaces.ICompleteUserProfile( context, None )
		except TypeError:
			profile = None
		else:
			if profile and profile.email:
				email = profile.email

		gravatar_type = None
		for x in (profile, context, self):
			gravatar_type = getattr( x, 'defaultGravatarType', None )
			if gravatar_type:
				break
		self.avatarURL = create_gravatar_url( email, gravatar_type )
