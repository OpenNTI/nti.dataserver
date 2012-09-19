#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters and utilities for working with avatar URLs.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import random

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from . import interfaces

from nti.utils import create_gravatar_url, GENERATED_GRAVATAR_TYPES


@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IAvatarURLProvider,interfaces.IAvatarURL)
def AvatarURLFactory(entity):
	"""
	For legacy reasons, this factory first checks for the presence of an avatar URL
	"""
	# Something explicitly set, historical
	if getattr( entity, '_avatarURL', None ):
		return _FixedAvatarWrapper( entity )

	return component.queryAdapter( entity, interfaces.IAvatarURLProvider, name="generated" )

@interface.implementer(interfaces.IAvatarURLProvider,interfaces.IAvatarURL)
class _FixedAvatarWrapper(object):

	def __init__( self, context ):
		self.avatarURL = getattr( context, '_avatarURL' )

# See also https://www.libravatar.org/
# for a FOSS Gravatar clone that supports delegation by domain.
# We may want to potentially run our own instance. It is written in Python.
# They provide pyLibravatar as a client library. The federation features
# use DNS and that library uses pyDNS which may or may not be gevent friendly,
# so that would have to be investigated

def _find_default_gravatar_type( *places ):
	for place in places:
		gravatar_type = getattr( place, 'defaultGravatarType', None )
		if gravatar_type:
			return gravatar_type


@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IAvatarURLProvider,interfaces.IAvatarURL)
class GravatarComputedAvatarURL(object):

	defaultGravatarType = 'identicon'

	def __init__( self, context ):

		email = context.username
		try:
			profile = interfaces.ICompleteUserProfile( context, None )
		except TypeError:
			profile = None
		else:
			if profile and profile.email:
				email = profile.email

		gravatar_type = _find_default_gravatar_type( profile, context, self )
		self.avatarURL = create_gravatar_url( email, gravatar_type )

@component.adapter(nti_interfaces.ICoppaUser)
@interface.implementer(interfaces.IAvatarURLProvider,interfaces.IAvatarURL)
class GravatarComputedCoppaAvatarURL(object):
	"""
	Coppa users aren't expected to have a valid email. Instead, they are
	expected to have choosen one of a few gravatar types or possibly permutations
	of usernames.
	"""

	defaultGravatarType = 'retro'

	def __init__( self, context ):
		gravatar_type = _find_default_gravatar_type( context, self )
		self.avatarURL = create_gravatar_url( context.username, gravatar_type )

@component.adapter(basestring)
@interface.implementer(interfaces.IAvatarChoices)
class StringComputedAvatarURLChoices(object):
	"""
	Computes a set of choices based of the given string. The assumption is that
	the given string is not a valid email address and so does not
	have any registered gravatars; thus, we get the different fallbacks.
	"""
	def __init__( self, context ):
		self.context = context

	def get_choices( self ):
		choices = []
		for name in (self.context, ''.join( list( reversed( self.context ) ) )):
			for gen_type in GENERATED_GRAVATAR_TYPES:
				choices.append( create_gravatar_url( name, gen_type ) )
		# Shuffle the choices so it's not obvious we're following a pattern to
		# create them. But shuffle them deterministically for the same input
		# so that we don't appear to jump around as we re-request this, which
		# would confuse the user
		random.Random( hash(self.context) ).shuffle( choices )
		return choices

@component.adapter(nti_interfaces.ICoppaUser)
@interface.implementer(interfaces.IAvatarChoices)
class GravatarComputedCoppaAvatarURLChoices(StringComputedAvatarURLChoices):

	def __init__( self, context ):
		super(GravatarComputedCoppaAvatarURLChoices,self).__init__( context.username )

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(interfaces.IAvatarChoices)
class EntityGravatarComputedAvatarURLChoices(object):
	"""
	Arbitrary entities just get their assigned URL.
	"""

	def __init__( self, context ):
		self.avatarURL = interfaces.IAvatarURL( context ).avatarURL

	def get_choices( self ):
		return (self.avatarURL,)


@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.IAvatarChoices)
class GravatarComputedAvatarURLChoices(object):
	"""
	Normal users get their "real" avatar URL, plus some based on creating
	a fake email address that cannot possibly be registered.
	"""

	def __init__( self, context ):
		self.avatarURL = interfaces.IAvatarURL( context ).avatarURL
		self.context = context

	def get_choices( self ):
		fake_addr = self.context.username.replace( '@', '_' ) + '@alias.nextthought.com'
		choices = StringComputedAvatarURLChoices( fake_addr ).get_choices()
		choices[0] = self.avatarURL
		return choices
