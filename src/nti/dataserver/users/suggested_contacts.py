#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import component
from zope import interface

from zope.container.contained import Contained

from nti.dataserver_core.interfaces import IUser

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ISuggestedContact
from .interfaces import ILimitedSuggestedContactsSource
from .interfaces import ISuggestedContactsProvider
from .interfaces import ISuggestedContactRankingPolicy

@total_ordering
@WithRepr
@EqHash("username", "rank")
@interface.implementer(ISuggestedContact)
class SuggestedContact(SchemaConfigured, Contained):
	createDirectFieldProperties(ISuggestedContact)

	@property
	def provider(self):
		return self.__dict__.get('_v_provider')

	@provider.setter
	def provider(self, nv):
		self.__dict__['_v_provider'] = nv

	def __lt__(self, other):
		try:
			return (self.rank, self.username) < (other.rank, other.username)
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.rank, self.username) > (other.rank, other.username)
		except AttributeError:
			return NotImplemented

@interface.implementer(ISuggestedContactRankingPolicy)
class SuggestedContactRankingPolicy(SchemaConfigured, Contained):
	createDirectFieldProperties(ISuggestedContactRankingPolicy)

	@classmethod
	def sort(cls, contacts):
		contacts = contacts or ()
		return sorted(contacts, reverse=True)
DefaultSuggestedContactRankingPolicy = SuggestedContactRankingPolicy

@interface.implementer(ISuggestedContactRankingPolicy)
class NoOpSuggestedContactRankingPolicy(SchemaConfigured, Contained):
	createDirectFieldProperties(ISuggestedContactRankingPolicy)

	@classmethod
	def sort(cls, contacts):
		return contacts

@interface.implementer(ISuggestedContactsProvider)
class DefaultSuggestedContactsProvider(SchemaConfigured, Contained):
	createDirectFieldProperties(ISuggestedContactsProvider)

	@property
	def priority(self):
		result = getattr(self.ranking, 'priority', None) or 1
		return result

	def suggestions(self, user):
		raise NotImplementedError()
SuggestedContactsProvider = DefaultSuggestedContactsProvider

@component.adapter(IUser)
@interface.implementer(ILimitedSuggestedContactsSource)
class _UserLimitedSuggestedContactSource(object):
	"""
	Based on the given user context, a limited number
	of suggested contacts will be returned.
	"""

	LIMIT = 1

	def __init__(self, context):
		self.source = context
		self.ranking = NoOpSuggestedContactRankingPolicy()
		self.ranking.provider = self
		
	def suggestions(self, user, *args, **kwargs):
		# And no dupes
		existing_pool = {e.username for e in user.entities_followed}
		entities_followed = {e.username for e in self.source.entities_followed}
		results = entities_followed - existing_pool
		return results[:self.LIMIT] if results else ()
