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

from zope.catalog.keyword import CaseInsensitiveKeywordIndex
import zope.catalog.field

import zope.index.field
import zope.index.topic
import zope.container.contained

from zope.index.topic.filter import FilteredSetBase

#: The name of the utility that the Zope Catalog
#: for users should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++entity-catalog'


# Old name for BWC
from nti.zope_catalog.index import CaseInsensitiveAttributeFieldIndex as CaseInsensitiveFieldIndex

from nti.zope_catalog.topic import TopicIndex

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

from zope.catalog.interfaces import ICatalog
from zc.intid import IIntIds

from zope.catalog.catalog import Catalog

def install_user_catalog( site_manager_container, intids=None ):
	lsm = site_manager_container.getSiteManager()
	if intids is None:
		intids = lsm.getUtility(IIntIds)

	catalog = Catalog(family=intids.family)
	catalog.__name__ = CATALOG_NAME
	catalog.__parent__ = site_manager_container
	intids.register( catalog )
	lsm.registerUtility( catalog, provided=ICatalog, name=CATALOG_NAME )

	for name, clazz in ( ('alias', AliasIndex),
						 ('email', EmailIndex),
						 ('contact_email', ContactEmailIndex),
						 ('password_recovery_email_hash', PasswordRecoveryEmailHashIndex),
						 ('realname', RealnameIndex),
						 ('realname_parts', RealnamePartsIndex),
						 ('contact_email_recovery_hash', ContactEmailRecoveryHashIndex)):
		index = clazz( family=intids.family )
		intids.register( index )
		# As a very minor optimization for unit tests, if we
		# already set the name and parent of the index,
		# the ObjectAddedEvent won't be fired
		# when we add the index to the catalog.
		# ObjectAdded/Removed events *must* fire during evolution,
		# though.
		index.__name__ = name; index.__parent__ = catalog; catalog[name] = index

	opt_in_comm_index = TopicIndex( family=intids.family)
	opt_in_comm_set = OptInEmailCommunicationFilteredSet( 'opt_in_email_communication',
														  family=intids.family)
	opt_in_comm_index.addFilter( opt_in_comm_set )
	intids.register( opt_in_comm_index )
	opt_in_comm_index.__name__ = 'topics'; opt_in_comm_index.__parent__ = catalog; catalog['topics'] = opt_in_comm_index

	return catalog
