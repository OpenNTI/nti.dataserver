#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes for indexing information related to users.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver.users import interfaces as user_interfaces

from zope.catalog.field import IFieldIndex
from zope.catalog.interfaces import ICatalogIndex
from zope.catalog.attribute import AttributeIndex
from zope.catalog.keyword import CaseInsensitiveKeywordIndex
import zope.catalog.field

import zope.index.field
import zope.index.topic
import zope.container.contained

from zope.index.topic.filter import FilteredSetBase

#: The name of the utility that the Zope Catalog
#: for users should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++entity-catalog'

@interface.implementer(IFieldIndex)
class NormalizingFieldIndex(zope.index.field.FieldIndex,
							zope.container.contained.Contained):
	def normalize( self, value ):
		return value

	def index_doc(self, docid, value):
		super(NormalizingFieldIndex,self).index_doc( docid, self.normalize(value) )

	def apply( self, query ):
		return super(NormalizingFieldIndex,self).apply( tuple([self.normalize(x) for x in query]) )

class CaseInsensitiveFieldIndex(AttributeIndex,
								NormalizingFieldIndex):

	def normalize( self, value ):
		if value:
			value = value.lower()
		return value

class AliasIndex(CaseInsensitiveFieldIndex):

	default_field_name = 'alias'
	default_interface = user_interfaces.IFriendlyNamed


class RealnameIndex(CaseInsensitiveFieldIndex):

	default_field_name = 'realname'
	default_interface = user_interfaces.IFriendlyNamed

class RealnamePartsIndex(CaseInsensitiveKeywordIndex):

	default_field_name = 'get_searchable_realname_parts'
	default_interface = user_interfaces.IFriendlyNamed

	def __init__( self, *args, **kwargs ):
		super(RealnamePartsIndex,self).__init__( *args, **kwargs )
		self.field_callable = True

class EmailIndex(CaseInsensitiveFieldIndex):

	default_field_name = 'email'
	default_interface = user_interfaces.IUserProfile

class ContactEmailIndex(CaseInsensitiveFieldIndex):

	default_field_name = 'contact_email'
	default_interface = user_interfaces.IUserProfile

class PasswordRecoveryEmailHashIndex(zope.catalog.field.FieldIndex):

	default_field_name = 'password_recovery_email_hash'
	default_interface = user_interfaces.IRestrictedUserProfile

class ContactEmailRecoveryHashIndex(zope.catalog.field.FieldIndex):

	default_field_name = 'contact_email_recovery_hash'
	default_interface = user_interfaces.IContactEmailRecovery


class OptInEmailCommunicationFilteredSet(FilteredSetBase):

	def __init__( self, id, family=None ):
		super(OptInEmailCommunicationFilteredSet,self).__init__( id, 'user_interfaces.IUserProfile(context).opt_in_email_communication', family=family )

	def index_doc( self, docid, context ):
		try:
			index = user_interfaces.IUserProfile(context).opt_in_email_communication
		except (TypeError,AttributeError):
			# Could not adapt, not in profile
			index = False

		if index:
			self._ids.insert( docid )
		else:
			# The normal PythonFilteredSet seems to have a bug and never unindexes?
			self.unindex_doc( docid )

@interface.implementer(ICatalogIndex)
class TopicIndex(zope.index.topic.TopicIndex,
				 zope.container.contained.Contained):
	"""
	A topic index that implements IContained and ICatalogIndex for use with
	OptInEmailCommunicationFilteredSet.
	"""

	# If we're not IContained, we get location proxied.

	# If we're not ICatalogIndex, we don't get updated when
	# we get put in a catalog.
