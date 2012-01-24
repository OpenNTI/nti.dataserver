#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )
import os

from .. import dataserver
from ..dataserver.users import User

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

class SocketPresenceExtension(SocketPresenceLayer,dataserver.sessions.Session):

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




class UserChangeLayer( context.layers.Layer ):

	def __init__( self ):
		super(UserChangeLayer,self).__init__()

	def active( self ):
		# TODO: What should this condition be?
		return True

class UserChangeExtension( UserChangeLayer, User ):
	@context.layers.after
	def _broadcastIncomingChange( self, ctx, change ):
		try:
			logger.debug( 'Broadcasting incoming change to %s chg: %s pid: %s', self.username, change, os.getpid() )
			_get_shared_dataserver().chatserver.notify_data_change( self.username, change )
		except Exception:
			logger.exception( 'Failed to notify data change' )

	@context.layers.after
	def _noticeChange( self, ctx, change ):
		try:
			# For the things that we ordinarily wouldn't
			# broadcast over APNS, we still want to distribute
			# to connected clients
			if change.type in (change.MODIFIED,change.DELETED):
				logger.debug( 'notice incoming change to %s chg: %s pid: %s', self.username, change, os.getpid() )
				_get_shared_dataserver().chatserver.notify_data_change( self.username, change )
		except Exception:
			logger.exception( 'Failed to notify data change' )


def register_implicit_layers():
	context.layers.register_implicit( SocketPresenceLayer() )
	context.layers.register_implicit( UserChangeLayer() )
