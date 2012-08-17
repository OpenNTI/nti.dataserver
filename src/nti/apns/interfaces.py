#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"Interfaces for dealing with Apple Push Notification Service"

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import schema

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

@interface.implementer(IDeviceFeedbackEvent)
class APNSDeviceFeedback(object):
	""" Represents feedback about a device from APNS. """

	def __init__( self, timestamp, deviceId ):
		super(APNSDeviceFeedback,self).__init__()
		self.timestamp = timestamp
		self.deviceId = deviceId

	def __repr__( self ):
		return "APNSDeviceFeedback(%s,%s)" % (self.timestamp, self.deviceId.encode('hex'))


class INotificationPayload(interface.Interface):
	"""
	The payload to send in a notification. Any action associated with
	an alert message should not be destructive---for example, deleting
	data on the device.

	Apple `documents the payload`_ values.

	.. _documents the payload: http://developer.apple.com/library/ios/#DOCUMENTATION/NetworkingInternet/Conceptual/RemoteNotificationsPG/ApplePushService/ApplePushService.html#//apple_ref/doc/uid/TP40008194-CH100-SW1
	""" # Idiotic apple links. I have no confidence that will actually work tomorrow. I mean, look at it


	alert = schema.TextLine(
		title="A short, localized string giving the text to display.",
		description="""
			The message text of an alert with two buttons: Close and View. If the user taps View, the application is launched.

			Note that although the APNS service technically support a dictionary for this property, allowing for app-side
			localization, that is not currently supported by this API.""")
	badge = schema.Int( title="The integer to badge the icon with or ``None``",
							required=False )
	sound = schema.TextLine( title="A string naming the sound to play",
									description="Either the string ``default``, meaning the default sound, or the name of a sound in the application bundle." )
	userInfo = schema.Dict(
		title="If not-``None``, a small dictionary of data to encode as JSON and send.",
		key_type=schema.TextLine(title="JSON property names"),
		required=False,
		description="""
			Custom values must use the JSON structured
			and primitive types: dictionary (object), array, string, number, and Boolean.
			You should not include customer information as custom
			payload data. Instead, use it for such purposes as setting
			context (for the user interface) or internal metrics.

			For example, a custom payload value might be a
			conversation identifier for use by an instant-message
			client application or a timestamp identifying when the
			provider sent the notification."""	)

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
