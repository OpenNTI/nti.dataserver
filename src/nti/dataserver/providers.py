#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import datastructures
from nti.ntiids import ntiids
from nti.dataserver import authorization as auth
from nti.dataserver.authorization_acl import ace_allowing, ace_denying

class _ClassMap(datastructures.AbstractCaseInsensitiveNamedLastModifiedBTreeContainer):

	contained_type = nti_interfaces.IClassInfo
	container_name = 'Classes'
	__name__ = container_name

@interface.implementer( nti_interfaces.IProviderOrganization )
class Provider(users.User):
	"""
	Represents a provider in the system.
	"""

	_ds_namespace = 'providers'

	@classmethod
	def create_provider( cls, *args, **kwargs ):
		return cls.create_user( *args, _stack_adjust=2, **kwargs )

	# For now, we model providers as user
	# objects so that they can act as resource containers and
	# hold Classes
	def __init__( self, username, *args, **kwargs ):
		if '@' in username:
			raise ValueError( "Providers do not use @" )
		# Yet we must fake out the superclass
		username = username + '@nextthought.com'

		super(Provider,self).__init__( username, *args, **kwargs )
		self.classes = _ClassMap()
		self.containers.addContainer( 'Classes', self.classes )
		self.classes.__parent__ = self
		# Strip the '@'
		self.username = self.username.split( '@' )[0]
		# Providers don't have friends or devices
		for k in ('FriendsLists', 'Devices'):
			try:
				self.containers.deleteContainer( k )
			except KeyError:
				pass

	def __setstate__( self, state ):
		super(Provider,self).__setstate__( state )
		# Providers don't have friends or devices
		for k in ('FriendsLists', 'Devices'):
			try:
				self.containers.deleteContainer( k )
			except KeyError:
				pass
		if self.classes.__parent__ is None:
			self.classes.__parent__ = self

	def get_by_ntiid( self, container_id ):
		result = super(Provider,self).get_by_ntiid( container_id )
		if not result:
			id_type = ntiids.get_type( container_id )
			def _match( x ):
				return x if getattr( x, 'NTIID', None ) == container_id else None

			# TODO: Generalize this
			# TODO: Should we track updates here?
			# TODO: Why are there two id_type that mean the same?
			if id_type in (ntiids.TYPE_MEETINGROOM_CLASS, ntiids.TYPE_CLASS):
				for x in self.classes.itervalues():
					result = _match( x )
					if result: break
			elif id_type == ntiids.TYPE_MEETINGROOM_SECT:
				for c in self.classes.itervalues():
					for s in getattr( c, 'Sections', () ):
						result = _match( s )
						if result: break
					if result: break

		return result

@interface.implementer( nti_interfaces.IACLProvider )
@component.adapter( nti_interfaces.IProviderOrganization )
class _ProviderACLProvider(object):
	"""
	Creates ACLs using pseudo-roles within the provider's namespace.
	"""

	def __init__( self, provider ):
		self.provider = provider

	@property
	def __acl__(self):
		localname = self.provider.username.split( '@' )[0]
		acl = list()
		# These roles are obviously placeholders.
		acl.append( ace_allowing( "role:" + localname + ".Admin", nti_interfaces.ALL_PERMISSIONS ) )
		acl.append( ace_allowing( "role:" + localname + ".Instructor", auth.ACT_READ ) )
		acl.append( ace_allowing( "role:" + localname + ".Student", auth.ACT_READ ) )
		acl.append( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) )
		return acl
