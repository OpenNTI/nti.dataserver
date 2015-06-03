#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes for indexing information related to users.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zc.intid import IIntIds

from zope.catalog.field import FieldIndex
from zope.catalog.interfaces import ICatalog
from zope.catalog.keyword import CaseInsensitiveKeywordIndex

from zope.index.topic.filter import FilteredSetBase

from nti.zope_catalog.catalog import Catalog
from nti.zope_catalog.topic import TopicIndex

# Old name for BWC
from nti.zope_catalog.index import CaseInsensitiveAttributeFieldIndex as CaseInsensitiveFieldIndex

from .interfaces import IUserProfile
from .interfaces import IFriendlyNamed
from .interfaces import IContactEmailRecovery
from .interfaces import IRestrictedUserProfile

# : The name of the utility that the Zope Catalog
# : for users should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++entity-catalog'

IX_ALIAS = 'alias'
IX_EMAIL = 'email'
IX_TOPICS = 'topics'
IX_REALNAME = 'realname'
IX_CONTACT_EMAIL = 'contact_email'
IX_REALNAME_PARTS = 'realname_parts'
IX_CONTACT_EMAIL_RECOVERY_HASH = 'contact_email_recovery_hash'
IX_PASSWORD_RECOVERY_EMAIL_HASH = 'password_recovery_email_hash'

IX_EMAIL_VERIFIED = 'email_verified'
IX_OPT_IN_EMAIL_COMMUNICATION = 'opt_in_email_communication'

class AliasIndex(CaseInsensitiveFieldIndex):

	default_field_name = IX_ALIAS
	default_interface = IFriendlyNamed

class RealnameIndex(CaseInsensitiveFieldIndex):

	default_field_name = IX_REALNAME
	default_interface = IFriendlyNamed

class RealnamePartsIndex(CaseInsensitiveKeywordIndex):

	default_field_name = 'get_searchable_realname_parts'
	default_interface = IFriendlyNamed

	def __init__(self, *args, **kwargs):
		super(RealnamePartsIndex, self).__init__(*args, **kwargs)
		self.field_callable = True

class EmailIndex(CaseInsensitiveFieldIndex):

	default_field_name = IX_EMAIL
	default_interface = IUserProfile

class ContactEmailIndex(CaseInsensitiveFieldIndex):

	default_field_name = IX_CONTACT_EMAIL
	default_interface = IUserProfile

class PasswordRecoveryEmailHashIndex(FieldIndex):

	default_field_name = IX_PASSWORD_RECOVERY_EMAIL_HASH
	default_interface = IRestrictedUserProfile

class ContactEmailRecoveryHashIndex(FieldIndex):

	default_field_name = IX_CONTACT_EMAIL_RECOVERY_HASH
	default_interface = IContactEmailRecovery

# XXX Note that FilteredSetBase uses a BTrees Set by default,
# NOT a TreeSet. So updating them when large is quite expensive.
# You can override clear() to use a TreeSet.
# TODO: Investigate migrating these two indexes to use a TreeSet,
# they have a size equal to the number of users and will conflict
# if many users are added at once.

class OptInEmailCommunicationFilteredSet(FilteredSetBase):

	EXPR = 'IUserProfile(context).opt_in_email_communication'

	def __init__(self, iden, family=None):
		super(OptInEmailCommunicationFilteredSet, self).__init__(iden, self.EXPR, family=family)

	def index_doc(self, docid, context):
		try:
			index = IUserProfile(context).opt_in_email_communication
		except (TypeError, AttributeError):
			# Could not adapt, not in profile
			index = False

		if index:
			self._ids.insert(docid)
		else:
			# The normal PythonFilteredSet seems to have a bug and never unindexes?
			self.unindex_doc(docid)

class EmailVerifiedFilteredSet(FilteredSetBase):

	EXPR = 'IUserProfile(context).email_verified'

	def __init__(self, iden, family=None):
		super(EmailVerifiedFilteredSet, self).__init__(iden, self.EXPR, family=family)

	def index_doc(self, docid, context):
		try:
			index = IUserProfile(context).email_verified
		except (TypeError, AttributeError):
			# Could not adapt, not in profile
			index = False

		if index:
			self._ids.insert(docid)
		else:
			# The normal PythonFilteredSet seems to have a bug and never unindexes?
			self.unindex_doc(docid)

def install_user_catalog(site_manager_container, intids=None):
	lsm = site_manager_container.getSiteManager()
	if intids is None:
		intids = lsm.getUtility(IIntIds)

	catalog = Catalog(family=intids.family)
	catalog.__name__ = CATALOG_NAME
	catalog.__parent__ = site_manager_container
	intids.register(catalog)
	lsm.registerUtility(catalog, provided=ICatalog, name=CATALOG_NAME)

	for name, clazz in ((IX_ALIAS, AliasIndex),
						(IX_EMAIL, EmailIndex),
						(IX_REALNAME, RealnameIndex),
						(IX_CONTACT_EMAIL, ContactEmailIndex),
						(IX_REALNAME_PARTS, RealnamePartsIndex),
						(IX_CONTACT_EMAIL_RECOVERY_HASH, ContactEmailRecoveryHashIndex),
						(IX_PASSWORD_RECOVERY_EMAIL_HASH, PasswordRecoveryEmailHashIndex)):
		index = clazz(family=intids.family)
		intids.register(index)
		# As a very minor optimization for unit tests, if we
		# already set the name and parent of the index,
		# the ObjectAddedEvent won't be fired
		# when we add the index to the catalog.
		# ObjectAdded/Removed events *must* fire during evolution,
		# though.
		index.__name__ = name
		index.__parent__ = catalog
		catalog[name] = index

	opt_in_comm_set = OptInEmailCommunicationFilteredSet(IX_OPT_IN_EMAIL_COMMUNICATION,
														 family=intids.family)

	email_verified_set = EmailVerifiedFilteredSet(IX_EMAIL_VERIFIED, family=intids.family)

	topics_index = TopicIndex(family=intids.family)
	topics_index.addFilter(opt_in_comm_set)
	topics_index.addFilter(email_verified_set)
	intids.register(topics_index)

	topics_index.__name__ = IX_TOPICS
	topics_index.__parent__ = catalog
	catalog[IX_TOPICS] = topics_index
	return catalog
