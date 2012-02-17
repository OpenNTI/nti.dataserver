#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

import os

from nti import dataserver
from nti.dataserver.users import User

import nti.dataserver.interfaces as nti_interfaces

from zope import component

######
# Notification Layers
######

def _get_shared_dataserver(context=None):
	return component.getUtility( nti_interfaces.IDataserver, context=context )

import context.layers
class SocketPresenceLayer(context.layers.Layer):

	def __init__( self ):
		super(SocketPresenceLayer,self).__init__()

	def active( self ):
		return True

class SocketPresenceExtension(SocketPresenceLayer, dataserver.sessions.Session):

	@context.layers.before
	def kill(self, ctx):
		if self.connected and self.owner:
			ds = _get_shared_dataserver()
			has_me_in_buddy_list = ()
			with ds.dbTrans():
				user = User.get_user( self.owner, dataserver=ds )
				# TODO: Better algorithm
				has_me_in_buddy_list = user.following | set(user._sources_accepted)
			ds.chatserver.notify_presence_change( self.owner,'Offline', has_me_in_buddy_list )

	@context.layers.after
	def incr_hits( self, ctx ):
		if self.connected and self.connection_confirmed and self.owner and not getattr( self, '_broadcast_connect', False):
			setattr( self, '_broadcast_connect', True )
			# We've just become connected for the first time
			ds = _get_shared_dataserver()
			has_me_in_buddy_list = ()
			with ds.dbTrans():
				user = User.get_user( self.owner, dataserver=ds )
				has_me_in_buddy_list = user.following | set(user._sources_accepted)
			ds.chatserver.notify_presence_change( self.owner,'Online', has_me_in_buddy_list )


def register_implicit_layers():
	context.layers.register_implicit( SocketPresenceLayer() )
