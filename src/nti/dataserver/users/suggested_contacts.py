#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import interface
from zope.container.contained import Contained

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ISuggestedContact
from .interfaces import ISuggestedContactsContext
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
class DefaultSuggestedContactRankingPolicy(object):
	
	@classmethod
	def sort(cls, contacts):
		contacts = contacts or ()
		return sorted(contacts, reverse=True)
SuggestedContactRankingPolicy = DefaultSuggestedContactRankingPolicy 

@interface.implementer(ISuggestedContactsContext)
class DefaultSuggestedContactsContext(object):
	priority = 1
SuggestedContactsContext = DefaultSuggestedContactsContext 

@interface.implementer(ISuggestedContactsProvider)
class DefaultSuggestedContactsProvider(SchemaConfigured, Contained):
	createDirectFieldProperties(ISuggestedContactsProvider)
	
	@property
	def priority(self):
		result = getattr(self.context, 'priority', None) or 1
		return result
	
	def suggestions(self, user):
		raise NotImplementedError()
SuggestedContactsProvider = DefaultSuggestedContactsProvider 
