#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constants and types for dealing with our unique IDs.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import numbers
from abc import ABCMeta, abstractmethod

from zope import component
from zope import interface

from zope.deprecation import deprecated

from nti.assessment import interfaces as asm_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import authorization_acl as nacl
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import interfaces as nid_interfaces

from nti.ntiids.ntiids import TYPE_MEETINGROOM_CLASS
deprecated( "TYPE_MEETINGROOM_CLASS", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM_CLASS" )
from nti.ntiids.ntiids import unicode_literals
deprecated( "unicode_literals", "Prefer nti.ntiids.ntiids.unicode_literals" )
from nti.ntiids.ntiids import InvalidNTIIDError
deprecated( "InvalidNTIIDError", "Prefer nti.ntiids.ntiids.InvalidNTIIDError" )
from nti.ntiids.ntiids import datetime
deprecated( "datetime", "Prefer nti.ntiids.ntiids.datetime" )
from nti.ntiids.ntiids import TYPE_MEETINGROOM_GROUP
deprecated( "TYPE_MEETINGROOM_GROUP", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM_GROUP" )
from nti.ntiids.ntiids import TYPE_MEETINGROOM
deprecated( "TYPE_MEETINGROOM", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM" )
from nti.ntiids.ntiids import TYPE_ROOM
deprecated( "TYPE_ROOM", "Prefer nti.ntiids.ntiids.TYPE_ROOM" )
from nti.ntiids.ntiids import DATE
deprecated( "DATE", "Prefer nti.ntiids.ntiids.DATE" )
from nti.ntiids.ntiids import TYPE_TRANSCRIPT_SUMMARY
deprecated( "TYPE_TRANSCRIPT_SUMMARY", "Prefer nti.ntiids.ntiids.TYPE_TRANSCRIPT_SUMMARY" )
from nti.ntiids.ntiids import validate_ntiid_string
deprecated( "validate_ntiid_string", "Prefer nti.ntiids.ntiids.validate_ntiid_string" )
from nti.ntiids.ntiids import TYPE_MEETINGROOM_SECT
deprecated( "TYPE_MEETINGROOM_SECT", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM_SECT" )
from nti.ntiids.ntiids import TYPE_QUIZ
deprecated( "TYPE_QUIZ", "Prefer nti.ntiids.ntiids.TYPE_QUIZ" )
from nti.ntiids.ntiids import TYPE_OID
deprecated( "TYPE_OID", "Prefer nti.ntiids.ntiids.TYPE_OID" )
from nti.ntiids.ntiids import is_valid_ntiid_string
deprecated( "is_valid_ntiid_string", "Prefer nti.ntiids.ntiids.is_valid_ntiid_string" )
from nti.ntiids.ntiids import NTIID
deprecated( "NTIID", "Prefer nti.ntiids.ntiids.NTIID" )

from nti.ntiids.ntiids import ROOT
deprecated( "ROOT", "Prefer nti.ntiids.ntiids.ROOT" )
from nti.ntiids.ntiids import get_provider
deprecated( "get_provider", "Prefer nti.ntiids.ntiids.get_provider" )
from nti.ntiids.ntiids import get_specific
from nti.ntiids.ntiids import is_ntiid_of_type
deprecated( "is_ntiid_of_type", "Prefer nti.ntiids.ntiids.is_ntiid_of_type" )
from nti.ntiids.ntiids import escape_provider
deprecated( "escape_provider", "Prefer nti.ntiids.ntiids.escape_provider" )
from nti.ntiids.ntiids import TYPE_TRANSCRIPT
deprecated( "TYPE_TRANSCRIPT", "Prefer nti.ntiids.ntiids.TYPE_TRANSCRIPT" )
from nti.ntiids.ntiids import get_parts
deprecated( "get_parts", "Prefer nti.ntiids.ntiids.get_parts" )
from nti.ntiids.ntiids import print_function
deprecated( "print_function", "Prefer nti.ntiids.ntiids.print_function" )
from nti.ntiids.ntiids import TYPE_CLASS_SECTION
deprecated( "TYPE_CLASS_SECTION", "Prefer nti.ntiids.ntiids.TYPE_CLASS_SECTION" )
from nti.ntiids.ntiids import get_type
deprecated( "get_type", "Prefer nti.ntiids.ntiids.get_type" )
from nti.ntiids.ntiids import time
deprecated( "time", "Prefer nti.ntiids.ntiids.time" )
from nti.ntiids.ntiids import make_ntiid
deprecated( "make_ntiid", "Prefer nti.ntiids.ntiids.make_ntiid" )
from nti.ntiids.ntiids import TYPE_HTML
deprecated( "TYPE_HTML", "Prefer nti.ntiids.ntiids.TYPE_HTML" )
from nti.ntiids.ntiids import TYPE_CLASS
deprecated( "TYPE_CLASS", "Prefer nti.ntiids.ntiids.TYPE_CLASS" )

from nti.ntiids.ntiids import find_object_with_ntiid
deprecated( "find_object_with_ntiid", "Prefer nti.ntiids.ntiids.find_object_with_ntiid" )

@interface.implementer( nid_interfaces.INTIIDResolver )
class _OIDResolver(object):

	def resolve( self, key ):
		dataserver = component.queryUtility( nti_interfaces.IDataserver )
		try:
			return dataserver.get_by_oid( key, ignore_creator=True ) if dataserver else None
		except ValueError:
			# Unpacking an OID key can raise ValueError if its in the wrong format
			logger.debug( "Invalid OID NTIID %s", key, exc_info=True )
			return None # per our spec

def _resolve_user( provider_name, namespace ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	user = None
	if dataserver:
		user = dataserver.root[namespace].get( provider_name )
		if not user:
			# Try unescaping it. See ntiids.py for more. The transformation is
			# not totally reliable. The - becomes _ when "escaped" (as does whitespace,
			# but those aren't allowed in user names). This wouldn't be a problem except that
			# usernames can contain - already. So if the name mixes _ and -, then we can't
			# recover it
			provider_name = provider_name.replace( '_', '-' )
			user = dataserver.root[namespace].get( provider_name )

	return user

@interface.implementer( nid_interfaces.INTIIDResolver )
class _NamedEntityResolver(object):

	def resolve( self, key ):
		# TODO: We currently know that everything we support, users and
		# communities, live in the same namespace
		ent_name = get_specific( key )
		return _resolve_user( ent_name, 'users' )

def _match( x, container_id, case_sensitive=True ):
	"""
	Things that are user-like, or might have their NTIID used like a Username
	and share that namespace, are expected to be treated case *in*sensitively.
	You should also configure a lowercase resolver.
	"""
	if case_sensitive:
		return x if getattr( x, 'NTIID', None ) == container_id else None

	#warnings.warn( "Hack for UI: making some NTIIDS case-insensitive." )
	return x if getattr( x, 'NTIID', '' ).lower() == (container_id.lower() or 'B').lower() else None

class AbstractUserBasedResolver(object):
	"""
	A base class for resolving NTIIDs within the context of a user
	(or other globally named entity). The incoming NTIID should name
	such an entity in its "provider" portion. This class then
	resolves the entity and passes it, along with the incoming
	NTIID string, to the :meth:`_resolve` method.

	"""
	__metaclass__ = ABCMeta

	namespace = 'users'

	#: Set this to an interface derived from :class:`.IEntity` to enforce
	#: a particular type of globally named entity.
	required_iface = nti_interfaces.IEntity

	def resolve( self, ntiid ):
		provider_name = get_provider( ntiid )
		user = _resolve_user( provider_name, self.namespace )

		if user and self.required_iface.providedBy( user ):
			return self._resolve( ntiid, user )

	@abstractmethod
	def _resolve( self, ntiid, user ):
		"""Subclasses implement this to finish the resolution in the scope of a user."""
		raise NotImplementedError()

_AbstractUserBasedResolver = AbstractUserBasedResolver # BWC

class AbstractAdaptingUserBasedResolver(AbstractUserBasedResolver):
	"""
	Adapts the found user to some interface and returns that or the default value.
	"""

	default_value = None
	adapt_to = None

	def _resolve( self, ntiid, user ):
		return component.queryAdapter( user, self.adapt_to, default=self.default_value )

class AbstractMappingAdaptingUserBasedResolver(AbstractAdaptingUserBasedResolver):
	"""
	Looks up the specific part of the ntiid in a mapping-like object (IContainer)
	adapted from the user.
	"""

	def _resolve( self, ntiid, user ):
		mapping = super(AbstractMappingAdaptingUserBasedResolver,self)._resolve( ntiid, user )
		if mapping is not None:
			return mapping.get( get_specific( ntiid ) )

@interface.implementer( nid_interfaces.INTIIDResolver )
class _ContentResolver(object):

	def resolve( self, key ):
		result = None
		library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
		path = library.pathToNTIID( key ) if library else None
		if path:
			result = path[-1]
			# TODO: ACL Proxy can probably go away
			result = nti_interfaces.ACLLocationProxy( result, result.__parent__, result.__name__, nacl.ACL( result ) )
		return result

@interface.implementer( nid_interfaces.INTIIDResolver )
class _AssessmentResolver(object):

	def resolve( self, key ):
		result = component.queryUtility( asm_interfaces.IQuestionMap, default={} ).get( key )
		if result:
			# TODO: ACL Proxy can probably go away
			result = nti_interfaces.ACLLocationProxy( result,
													  getattr( result, '__parent__', None ),
													  getattr( result, '__name__', None ),
													  nacl.ACL( result ) )
		return result

@interface.implementer( nid_interfaces.INTIIDResolver )
class _MeetingRoomResolver(_AbstractUserBasedResolver):

	def _resolve( self, key, user ):
		result = None
		for x in user.friendsLists.itervalues():
			if _match( x, key, False ):
				result = x
				break
		return result

@interface.implementer( nid_interfaces.INTIIDResolver )
class _TranscriptResolver(_AbstractUserBasedResolver):

	def _resolve( self, key, user ):
		result = chat_interfaces.IUserTranscriptStorage(user).transcript_for_meeting( key )
		if result is None: # bool is based on messages
			logger.debug( "Failed to find transcript given oid: %s", key )
		return result

@interface.implementer( nid_interfaces.INTIIDResolver )
class _UGDResolver(_AbstractUserBasedResolver):

	def _resolve( self, key, user ):
		# Try looking up the ntiid by name in each container
		# TODO: This is terribly expensive
		if not nti_interfaces.IUser.providedBy( user ):
			# NOTE: We are abusing this interface. We actually look
			# at a property not defined by this interface, user.containers.
			# We really want nti_interfaces.IContainerIterable, but cannot use it.
			# This is because of the inconsistency in the way it is defined and implemented.
			return None

		result = None
		for container_name in user.containers.containers:
			container = user.containers.containers[container_name]
			if isinstance( container, numbers.Number ): continue
			result = container.get( key )
			if result:
				break
		return result
