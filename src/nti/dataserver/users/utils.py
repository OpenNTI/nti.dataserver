#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid

from zope import component
from zope.catalog.interfaces import ICatalog

from .index import IX_EMAIL
from .index import IX_TOPICS
from .index import CATALOG_NAME
from .index import IX_EMAIL_VERIFIED

from .interfaces import IUserProfile

def verified_email_ids(email):
	email = email.lower() # normalize
	catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

	# all ids w/ this email
	email_idx = catalog[IX_EMAIL]
	intids_emails = catalog.family.IF.Set(email_idx._fwd_index.get(email) or ())
	if not intids_emails:
		return catalog.family.IF.Set()
	
	# all verified emails 
	verifed_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]	
	intids_verified = catalog.family.IF.Set(verifed_idx.getIds())
	
	# intersect
	result = catalog.family.IF.intersection(intids_emails, intids_verified)
	return result

def reindex_email_verification(user):
	intids = component.getUtility(zope.intid.IIntIds)
	uid = intids.queryId(user)
	if uid is not None:
		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		verifed_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
		verifed_idx.index_doc(uid, user)
		return True
	return False

def unindex_email_verification(user):
	intids = component.getUtility(zope.intid.IIntIds)
	uid = intids.queryId(user)
	if uid is not None:
		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		verifed_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
		verifed_idx.unindex_doc(uid, user)
		return True
	return False
	
def force_email_verification(user, profile_iface=IUserProfile):
	profile = profile_iface(user, None)   
	if profile is not None:   
		profile.email_verified = True
		return reindex_email_verification(user)
	return False
	
def is_email_verified(email):
	result = verified_email_ids(email)
	return bool(result)
