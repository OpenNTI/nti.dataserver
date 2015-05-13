#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.intid import IIntIds

from zope import component
from zope.catalog.interfaces import ICatalog

from .index import IX_EMAIL
from .index import IX_TOPICS
from .index import CATALOG_NAME
from .index import IX_EMAIL_VERIFIED

from .interfaces import IUserProfile

def get_catalog():
	return component.getUtility(ICatalog, name=CATALOG_NAME)

def verified_email_ids(email):
	email = email.lower() # normalize
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

	# all ids w/ this email
	email_idx = catalog[IX_EMAIL]
	intids_emails = catalog.family.IF.Set(email_idx._fwd_index.get(email) or ())
	if not intids_emails:
		return catalog.family.IF.Set()

	# all verified emails
	verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
	intids_verified = catalog.family.IF.Set(verified_idx.getIds())

	# intersect
	result = catalog.family.IF.intersection(intids_emails, intids_verified)
	return result

def reindex_email_verification(user, catalog=None, intids=None):
	catalog = catalog if catalog is not None else get_catalog()
	intids = component.getUtility(IIntIds) if intids is None else intids
	uid = intids.queryId(user)
	if uid is not None:
		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
		verified_idx.index_doc(uid, user)
		return True
	return False

def unindex_email_verification(user, catalog=None, intids=None):
	catalog = catalog if catalog is not None else get_catalog()
	intids = component.getUtility(IIntIds) if intids is None else intids
	uid = intids.queryId(user)
	if uid is not None:
		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
		verified_idx.unindex_doc(uid)
		return True
	return False

def force_email_verification(user, profile=IUserProfile, catalog=None, intids=None):
	profile = profile(user, None)
	if profile is not None:
		profile.email_verified = True
		return reindex_email_verification(user, catalog=catalog, intids=intids)
	return False

def is_email_verified(email):
	result = verified_email_ids(email)
	return bool(result)
