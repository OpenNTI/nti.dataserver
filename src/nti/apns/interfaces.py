#!/usr/bin/env python
"Interfaces for dealing with Apple Push Notification Service"

from zope import interface

class IDeviceFeedback(interface.Interface):
	"""
	Feedback about an invalid device received from APNS.
	"""

	timestamp = interface.Attribute( "The timestamp of the notification?" )
	deviceId = interface.Attribute( "The raw bytes of the device being de-registered.")

class IDeviceFeedbackEvent(IDeviceFeedback):
	"""
	An event emitted when device feedback is received.
	"""

class INotificationPayload(interface.Interface):
	"""
	The payload to send in a notification.
	"""

	alert = interface.Attribute( "A string giving the text to display" )
	badge = interface.Attribute( "The integer to badge the icon with or None" )
	sound = interface.Attribute( "A string naming the sound to play" )
	userInfo = interface.Attribute( "If not-None, a small dictionary of data to encode as JSON and send." )

class INotificationService(interface.Interface):
	"""
	The interface to sending notifications.
	"""

	def sendNotification( deviceId, payload ):
		"""
		Asks for the device identified with the raw `deviceId` bytes to receive the
		data in the :class:`INotificationPayload` payload.
		"""

#	def reset(): pass

	def close(): pass
