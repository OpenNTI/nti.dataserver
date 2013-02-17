#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import time
import uuid
import collections
import six
import datetime

from persistent import Persistent
from persistent.list import PersistentList

from nti.utils.property import alias, read_alias

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.contentfragments import interfaces as frg_interfaces
from nti.contentfragments import censor

from nti.dataserver import mimetype
from nti.dataserver import sharing
from nti.dataserver.users import entity
from nti.dataserver import contenttypes
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.base import _make_getitem

from zope.deprecation import deprecate

from zope import interface
from zope import component
from zope.dublincore import interfaces as dc_interfaces
from zope.container.contained import contained

from . import interfaces

# TODO: MessageInfo is a mess. Unify better with IContent
# and the other content types.
# We manually re-implement IDCTimes (should extend CreatedModDateTrackingObject)
@interface.implementer( interfaces.IMessageInfo,
						dc_interfaces.IDCTimes)
class MessageInfo( sharing.AbstractReadableSharedMixin,
				   contenttypes.ThreadableMixin,
				   Persistent ):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	__parent__ = None

	__external_can_create__ = True

	_prefer_oid_ = False

	# The usernames of occupants of the initial room, and others
	# the transcript should go to. Set by policy.
	sharedWith = ()
	channel = interfaces.CHANNEL_DEFAULT
	body = None
	recipients = ()
	Creator = None # aka Sender. Forcibly set by the handler
	containerId = None

	def __init__( self ):
		super(MessageInfo,self).__init__()
		self.ID = uuid.uuid4().hex
		self._v_sender_sid = None # volatile. The session id of the sender.
		self.LastModified = time.time()
		self.CreatedTime = self.LastModified
		self.Status = interfaces.STATUS_INITIAL

	Sender = alias('Creator')
	creator = alias('Creator')

	# From AbstractReadableSharedMixin
	@property
	def sharingTargets(self):
		result = set()
		for x in self.sharedWith:
			x = entity.Entity.get_entity( x )
			if x:
				result.add( x )

		return result
	# From IWritableSharable
	def clearSharingTargets(self):
		self.sharedWith = MessageInfo.sharedWith
	# We don't really do sharing with entities, just usernames. So the entity-based
	# methods are not implemented
	def addSharingTarget(self, target ):
		raise NotImplementedError()
	def updateSharingTargets( self, replacements ):
		raise NotImplementedError()

	def setSharedWithUsernames( self, usernames ):
		self.sharedWith = usernames


	id = read_alias('ID')
	MessageId = read_alias('ID') # bwc
	__name__ = alias('ID')

	createdTime = alias('CreatedTime')
	lastModified = alias('LastModified')
	Timestamp = alias('LastModified') # bwc
	# IDCTimes
	created = property( lambda self: datetime.datetime.fromtimestamp( self.createdTime ),
						lambda self, dt: setattr( self, 'createdTime', time.mktime( dt.timetuple() ) ) )
	modified = property( lambda self: datetime.datetime.fromtimestamp( self.lastModified ),
						lambda self, dt: self.updateLastModIfGreater( time.mktime( dt.timetuple() ) ) )
	def updateLastModIfGreater( self, t ): # copied from ModDateTrackingObject
		"Only if the given time is (not None and) greater than this object's is this object's time changed."
		if t is not None and t > self.lastModified:
			self.lastModified = t
		return self.lastModified

	def updateLastMod( self ):
		pass

	def get_sender_sid( self ):
		"""
		When this message first arrives, this will
		be the session id of the session that sent
		the message. After that, it will be None.
		"""
		return getattr( self, '_v_sender_sid', None )
	def set_sender_sid( self, sid ):
		setattr( self, '_v_sender_sid', sid )
	sender_sid = property( get_sender_sid, set_sender_sid )

	@property
	def rooms( self ):
		return [self.containerId]

	Body = alias( 'body' )

	@property
	def recipients_without_sender(self):
		"""
		All the recipients of this message, excluding the Sender.
		"""
		recip = set( self.recipients )
		recip.discard( self.Sender )
		return recip

	@property
	def recipients_with_sender( self ):
		"""
		All the recipients of this message, including the Sender.
		"""
		recip = set( self.recipients )
		recip.add( self.Sender )
		return recip

	def is_default_channel( self ):
		return self.channel is None or self.channel == interfaces.CHANNEL_DEFAULT

	__getitem__ = _make_getitem( 'body' )

	__ext_ignore_toExternalObject__ = True
	@deprecate("Prefer to use nti.externalization directly.")
	def toExternalObject( self ):
		return to_external_object( self )

	__ext_ignore_updateFromExternalObject__ = True
	@deprecate("Prefer to use nti.externalization directly.")
	def updateFromExternalObject( self, ext_object, context=None ):
		return update_from_external_object( self, ext_object, context=context )

from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.dataserver.contenttypes.threadable import ThreadableExternalizableMixin
from zope.proxy import removeAllProxies

@component.adapter(interfaces.IMessageInfo)
class MessageInfoInternalObjectIO(ThreadableExternalizableMixin,ExternalizableInstanceDict):

	def __init__( self, context ):
		super(MessageInfoInternalObjectIO,self).__init__()
		self.context = context

	def _ext_replacement(self):
		return removeAllProxies(self.context)

	_excluded_in_ivars_ = { 'MessageId' } | ExternalizableInstanceDict._excluded_in_ivars_
	_update_accepts_type_attrs = True
	_prefer_oid_ = False

	def toExternalObject( self, mergeFrom=None ):
		result = super(MessageInfoInternalObjectIO,self).toExternalObject( mergeFrom=mergeFrom )
		msg = self.context
		if msg.body is not None:
			# alias for old code.
			result['Body'] = result['body']
		if 'channel' not in result:
			# Must not have been in the instance dict
			# TODO: Switch this to interface-driven
			result['channel'] = msg.channel
		if 'recipients' not in result:
			result['recipients'] = msg.recipients
		return result


	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(MessageInfoInternalObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )
		msg = self.context
		if 'Body' in parsed and 'body' not in parsed:
			msg.body = parsed['Body']
		if 'Body' or 'body' in parsed:
			# TODO: Switch to InterfaceIO to avoid doing this manually.
			if isinstance( msg.body, six.string_types ):
				msg.body = censor.censor_assign( frg_interfaces.IUnicodeContentFragment( msg.body ), msg, 'body' )
			elif isinstance( msg.body, collections.Sequence ):
				msg.body = [censor.censor_assign( frg_interfaces.IUnicodeContentFragment( x ), msg, 'body' ) if isinstance(x,six.string_types) else x
							 for x
							 in msg.body]
				for i, x in enumerate(msg.body):
					# Make images work
					if nti_interfaces.ICanvas.providedBy( x ):
						contained( x, msg, unicode(i) )

		# make recipients be stored as a persistent list.
		# In theory, this helps when we have to serialize the message object
		# into the database multiple times, by avoiding extra copies (like when we transcript)
		# This also results in us copying incoming recipients
		if msg.recipients and 'recipients' in parsed:
			msg.recipients = PersistentList( msg.recipients )
