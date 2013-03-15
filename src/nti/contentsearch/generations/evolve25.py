# -*- coding: utf-8 -*-
"""
Content search generation 25.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 25

import zope.intid
from zope import component
from zc import intid as zc_intid
from zope.component.hooks import site, setHooks

from ZODB.POSException import POSKeyError

from .. import _repoze_index
from .. import interfaces as search_interfaces
from ..constants import (redaction_, replacementContent_, redactionExplanation_)

from .evolve23 import reindex_redactions

def do_evolve(context):
	"""
	Reindex redactions if required.
	"""
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']
	lsm = ds_folder.getSiteManager()

	ds_intid = lsm.getUtility(provided=zope.intid.IIntIds)
	component.provideUtility(ds_intid, zope.intid.IIntIds)
	component.provideUtility(ds_intid, zc_intid.IIntIds)

	with site(ds_folder):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']

		# remove all post catalogs first
		for user in users.values():
			try:
				rim = search_interfaces.IRepozeEntityIndexManager(user, None)
				catalog = rim.get(redaction_, None)  if rim is not None else None
				if catalog is None:
					continue

				reindex = False
				if replacementContent_ not in catalog:
					reindex = True
					_repoze_index._zopytext_field_creator(catalog, replacementContent_, search_interfaces.IRedactionRepozeCatalogFieldCreator)
				if redactionExplanation_ not in catalog:
					reindex = True
					_repoze_index._zopytext_field_creator(catalog, redactionExplanation_, search_interfaces.IRedactionRepozeCatalogFieldCreator)

				if reindex:
					reindex_redactions(user, users.get, ds_intid)
			except POSKeyError:
				# broken reference for user
				pass

	logger.debug('Evolution done!!!')

def evolve(context):
	"""
	Evolve generation 24 to 25 by reindexing redactions if required
	"""
	do_evolve(context)
