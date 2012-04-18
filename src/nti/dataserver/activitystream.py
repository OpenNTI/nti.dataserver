#!/usr/bin/env python2.7

"""
Functions and architecture for general activity streams.
"""

import logging
logger = logging.getLogger(__name__)

import os
from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from zope import component

def enqueue_change( change, **kwargs ):
	ds = component.queryUtility( nti_interfaces.IDataserver )
	if ds:
		ds.enqueue_change( change, **kwargs )

@component.adapter( nti_interfaces.IUser, nti_interfaces.IStreamChangeEvent )
def user_change_broadcaster( user, change ):
	chatserver = component.queryUtility( chat_interfaces.IChatserver )
	if not chatserver:
		logger.debug( "Unable to broadcast notification, no chatserver" )
		return

	if chatserver:
		try:
			logger.debug( 'Broadcasting incoming change to %s chg: %s pid: %s', user.username, change.type, os.getpid() )
			chatserver.notify_data_change( user.username, change )
		except Exception:
			logger.exception( 'Failed to notify data change' )
