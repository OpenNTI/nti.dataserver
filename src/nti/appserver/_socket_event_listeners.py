#!/usr/bin/env python2.7

"""
Listeners for socket activity.
"""

import logging
logger = logging.getLogger(__name__)

from nti.dataserver import interfaces as nti_interfaces, users
from zope import component


def _notify_friends_of_presence( session, presence ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	chatserver = component.queryUtility( nti_interfaces.IChatserver )
	if dataserver is None or chatserver is None:
		logger.debug( "Unable to broadcast presence notification. DS: %s CS %s", dataserver, chatserver )
		return

	has_me_in_buddy_list = ()
	user = users.User.get_user( session.owner, dataserver=dataserver )
	if user is None:
		logger.error( "Unable to get owner of session %s; not sending presence notification", session )
		return

	# TODO: Better algorithm. Who should this really go to?
	has_me_in_buddy_list = user.following | set(user._sources_accepted)
	logger.debug( "Notifying %s of presence change of %s to %s", has_me_in_buddy_list, session.owner, presence )
	chatserver.notify_presence_change( session.owner, presence, has_me_in_buddy_list )

@component.adapter( nti_interfaces.ISocketSession, nti_interfaces.ISocketSessionDisconnectedEvent )
def session_disconnected_broadcaster( session, event ):
	_notify_friends_of_presence( session, 'Offline' )


@component.adapter( nti_interfaces.ISocketSession, nti_interfaces.ISocketSessionConnectedEvent )
def session_connected_broadcaster( session, event ):
	_notify_friends_of_presence( session, 'Online' )
