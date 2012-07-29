""" Chatserver functionality. """

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import time
import uuid
import collections
import six

from persistent import Persistent
from persistent.list import PersistentList

from nti.externalization import datastructures
from nti.contentfragments import interfaces as frg_interfaces

from nti.dataserver import contenttypes


from zope import interface
from zope import component

from . import interfaces

@interface.implementer( interfaces.IMessageInfo )
class MessageInfo( contenttypes.ThreadableExternalizableMixin,
				   Persistent,
				   datastructures.ExternalizableInstanceDict ):

	__parent__ = None

	__external_can_create__ = True

	_excluded_in_ivars_ = { 'MessageId' } | datastructures.ExternalizableInstanceDict._excluded_in_ivars_
	_update_accepts_type_attrs = True
	_prefer_oid_ = False

	# The usernames of occupants of the initial room, and others
	# the transcript should go to. Set by policy.
	sharedWith = ()
	channel = interfaces.CHANNEL_DEFAULT
	body = None
	recipients = ()

	def __init__( self ):
		super(MessageInfo,self).__init__()
		self.ID = uuid.uuid4().hex
		self.Creator = None # aka Sender. Forcibly set by the handler
		self._v_sender_sid = None # volatile. The session id of the sender.
		self.LastModified = time.time()
		self.CreatedTime = self.LastModified
		self.containerId = None
		self.Status = interfaces.STATUS_INITIAL

	# Aliases (TODO: Need general alias descriptor)
	def get_Sender(self):
		return self.Creator
	def set_Sender(self,s):
		self.Creator = s
	Sender = property( get_Sender, set_Sender )
	creator = Sender

	@property
	def id(self):
		return self.ID
	MessageId = id # bwc

	__name__ = property(lambda self: self.ID, lambda self, nn: setattr( self, 'ID', nn ))

	def get_createdTime(self):
		return self.CreatedTime
	def set_createdTime(self,st):
		self.CreatedTime = st
	createdTime = property(get_createdTime,set_createdTime)

	def get_lastModified(self):
		return self.LastModified
	def set_lastModified(self,lm):
		self.LastModified = lm
	lastModified = property(get_lastModified,set_lastModified)
	Timestamp = lastModified # bwc

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


	# Aliases for old code
	# @property
	# def MessageId( self ):
	# 	return self.ID

	# @property
	# def Timestamp(self):
	# 	return self.LastModified

	@property
	def rooms( self ):
		return [self.containerId]

	def get_Body( self ):
		return self.body
	def set_Body( self, body ):
		self.body = body
	Body = property( get_Body, set_Body )

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

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(MessageInfo,self).toExternalDictionary( mergeFrom=mergeFrom )
		if self.body is not None:
			# alias for old code.
			result['Body'] = result['body']
		if 'channel' not in result:
			# Must not have been in the instance dict
			# TODO: Switch this to interface-driven
			result['channel'] = self.channel
		if 'recipients' not in result:
			result['recipients'] = self.recipients
		return result

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(MessageInfo,self).updateFromExternalObject( parsed, *args, **kwargs )
		if 'Body' in parsed and 'body' not in parsed:
			self.body = parsed['Body']
		if 'Body' or 'body' in parsed:
			if isinstance( self.body, six.string_types ):
				self.body = frg_interfaces.IUnicodeContentFragment( self.body )
			elif isinstance( self.body, collections.Sequence ):
				self.body = [frg_interfaces.IUnicodeContentFragment( x ) if isinstance(x,six.string_types) else x
							 for x
							 in self.body]

		# make recipients be stored as a persistent list.
		# In theory, this helps when we have to serialize the message object
		# into the database multiple times, by avoiding extra copies (like when we transcript)
		# This also results in us copying incoming recipients
		if self.recipients and 'recipients' in parsed:
			self.recipients = PersistentList( self.recipients )
