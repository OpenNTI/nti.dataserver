#!/usr/bin/env python2.7

from zope import interface
from zope import component
from zope.component.factory import Factory
from zope.component.interfaces import IFactory

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import datastructures
from nti.dataserver import ntiids

class _ClassMap(datastructures.AbstractNamedContainerMap):

	contained_type = nti_interfaces.IClassInfo
	container_name = 'Classes'

class Provider(users.User):
	"""
	Represents a provider in the system.
	"""
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

	def get_by_ntiid( self, container_id ):
		result = super(Provider,self).get_by_ntiid( container_id )
		if not result:
			id_type = ntiids.get_type( container_id )
			def _match( x ):
				return x if getattr( x, 'NTIID', None ) == container_id else None

			# TODO: Generalize this
			# TODO: Should we track updates here?
			if id_type == ntiids.TYPE_MEETINGROOM_CLASS:
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
