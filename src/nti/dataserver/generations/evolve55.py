#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 55

from zope import component
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import site, setHooks

import BTrees

from ..users.index import IX_TOPICS
from ..users.index import CATALOG_NAME
from ..users.index import IX_EMAIL_VERIFIED
from ..users.index import EmailVerifiedFilteredSet

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	lsm = ds_folder.getSiteManager()
	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		ent_catalog = lsm.getUtility(provided=ICatalog, name=CATALOG_NAME)
		topics = ent_catalog[IX_TOPICS]
		try:
			email_verified_set = topics[IX_EMAIL_VERIFIED]
		except KeyError:
			email_verified_set = EmailVerifiedFilteredSet(IX_EMAIL_VERIFIED,
														 family=BTrees.family64)
			topics.addFilter( email_verified_set )
		
def evolve( context ):
	"""
	Evolve to generation 55 by adding a email_verified filter set index
	"""
	do_evolve(context)
