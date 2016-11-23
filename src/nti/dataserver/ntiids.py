#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constants and types for dealing with our unique IDs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import numbers
from abc import ABCMeta
from abc import abstractmethod

from zope import component
from zope import interface

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IDataserver

from nti.ntiids.interfaces import INTIIDResolver

from nti.ntiids.ntiids import ROOT

from nti.ntiids.ntiids import get_provider
from nti.ntiids.ntiids import get_specific

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
	"Moved to nti.ntiids.ntiids",
	"nti.ntiids.ntiids",
	"datetime",
	"unicode_literals",
	"InvalidNTIIDError",
	"TYPE_MEETINGROOM_CLASS",
	"TYPE_MEETINGROOM_GROUP",
	"TYPE_MEETINGROOM",
	"TYPE_ROOM",
	"DATE",
	"TYPE_TRANSCRIPT_SUMMARY",
	"validate_ntiid_string",
	"TYPE_MEETINGROOM_SECT",
	"TYPE_QUIZ",
	"TYPE_OID",
	"is_valid_ntiid_string",
	"NTIID",
	"ROOT",
	"get_parts",
	"get_provider",
	"get_specific",
	"is_ntiid_of_type",
	"escape_provider",
	"TYPE_TRANSCRIPT",
	"print_function",
	"time",
	"make_ntiid",
	"TYPE_HTML",
	"TYPE_CLASS",
	"find_object_with_ntiid")

NTIID_ROOT = ROOT  # re-export

@interface.implementer(INTIIDResolver)
class _OIDResolver(object):

	def resolve(self, key):
		dataserver = component.queryUtility(IDataserver)
		try:
			return dataserver.get_by_oid(key, ignore_creator=True) if dataserver else None
		except ValueError:
			# Unpacking an OID key can raise ValueError if its in the wrong format
			logger.debug("Invalid OID NTIID %s", key, exc_info=True)
			return None  # per our spec

def _resolve_user(provider_name, namespace):
	dataserver = component.queryUtility(IDataserver)
	user = None
	if dataserver:
		user = dataserver.root[namespace].get(provider_name)
		if not user:
			# Try unescaping it. See ntiids.py for more. The transformation is
			# not totally reliable. The - becomes _ when "escaped" (as does whitespace,
			# but those aren't allowed in user names). This wouldn't be a problem except that
			# usernames can contain - already. So if the name mixes _ and -, then we can't
			# recover it
			provider_name = provider_name.replace('_', '-')
			user = dataserver.root[namespace].get(provider_name)
	return user

@interface.implementer(INTIIDResolver)
class _NamedEntityResolver(object):

	def resolve(self, key):
		# TODO: We currently know that everything we support, users and
		# communities, live in the same namespace
		ent_name = get_specific(key)
		return _resolve_user(ent_name, 'users')

def _match(x, container_id, case_sensitive=True):
	"""
	Things that are user-like, or might have their NTIID used like a Username
	and share that namespace, are expected to be treated case *in*sensitively.
	You should also configure a lowercase resolver.
	"""
	if case_sensitive:
		return x if getattr(x, 'NTIID', None) == container_id else None

	# warnings.warn( "Hack for UI: making some NTIIDS case-insensitive." )
	return x if getattr(x, 'NTIID', '').lower() == (container_id.lower() or 'B').lower() else None

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
	required_iface = IEntity

	def resolve(self, ntiid):
		provider_name = get_provider(ntiid)
		user = _resolve_user(provider_name, self.namespace)

		if user and self.required_iface.providedBy(user):
			return self._resolve(ntiid, user)

	@abstractmethod
	def _resolve(self, ntiid, user):
		"""Subclasses implement this to finish the resolution in the scope of a user."""
		raise NotImplementedError()

_AbstractUserBasedResolver = AbstractUserBasedResolver  # BWC

class AbstractAdaptingUserBasedResolver(AbstractUserBasedResolver):
	"""
	Adapts the found user to some interface and returns that or the default value.
	"""

	adapt_to = None
	default_value = None

	def _resolve(self, ntiid, user):
		return component.queryAdapter(user, self.adapt_to, default=self.default_value)

class AbstractMappingAdaptingUserBasedResolver(AbstractAdaptingUserBasedResolver):
	"""
	Looks up the specific part of the ntiid in a mapping-like object (IContainer)
	adapted from the user.
	"""

	def _resolve(self, ntiid, user):
		mapping = super(AbstractMappingAdaptingUserBasedResolver, self)._resolve(ntiid, user)
		if mapping is not None:
			return mapping.get(get_specific(ntiid))
		return None

@interface.implementer(INTIIDResolver)
class _MeetingRoomResolver(_AbstractUserBasedResolver):

	def _resolve(self, key, user):
		result = None
		for x in user.friendsLists.itervalues():
			if _match(x, key, False):
				result = x
				break
		return result

@interface.implementer(INTIIDResolver)
class _TranscriptResolver(_AbstractUserBasedResolver):

	def _resolve(self, key, user):
		result = IUserTranscriptStorage(user).transcript_for_meeting(key)
		if result is None:  # bool is based on messages
			logger.debug("Failed to find transcript given oid: %s", key)
		return result

@interface.implementer(INTIIDResolver)
class _UGDResolver(_AbstractUserBasedResolver):

	def _resolve(self, key, user):
		# Try looking up the ntiid by name in each container
		# TODO: This is terribly expensive
		if not IUser.providedBy(user):
			# NOTE: We are abusing this interface. We actually look
			# at a property not defined by this interface, user.containers.
			# We really want nti_interfaces.IContainerIterable, but cannot use it.
			# This is because of the inconsistency in the way it is defined and implemented.
			return None

		result = None
		for container_name in user.containers.containers:
			container = user.containers.containers[container_name]
			if isinstance(container, numbers.Number):
				continue
			result = container.get(key)
			if result:
				break
		return result
