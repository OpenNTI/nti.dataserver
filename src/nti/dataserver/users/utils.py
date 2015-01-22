#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.catalog.interfaces import ICatalog

from .index import IX_EMAIL
from .index import IX_TOPICS
from .index import CATALOG_NAME
from .index import IX_EMAIL_VERIFIED

def verifed_email_ids(email):
    catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
    email = email.lower() # normalize
      
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

def is_email_verfied(email):
    result = verifed_email_ids(email)
    return bool(result)
