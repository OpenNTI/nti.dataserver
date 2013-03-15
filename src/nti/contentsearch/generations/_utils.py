# -*- coding: utf-8 -*-
"""
Content search generation utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid
from zope import component
from zc import intid as zc_intid
from ZODB.POSException import POSKeyError

from ..utils import find_all_indexable_pairs
from .. import interfaces as search_interfaces
from .. import _discriminators as discriminators
from ..utils._repoze_utils import remove_entity_indices

def reindex_ugd(user, users_get, ds_intid):
	username = user.username
	logger.debug('Reindexing object(s) for %s' % username)

	counter = 0
	for e, obj in find_all_indexable_pairs(user):
		try:
			rim = search_interfaces.IRepozeEntityIndexManager(e, None)
			catalog = rim.get_create_catalog(obj) if rim is not None else None
			if catalog is not None:
				docid = discriminators.query_uid(obj, ds_intid)
				if docid is not None:
					catalog.index_doc(docid, obj)
					counter = counter + 1
				else:
					logger.warn("Cannot find int64 id for %r. Object will not be indexed" % obj)
		except POSKeyError:
			pass

	logger.debug('%s object(s) for user %s were reindexed' % (counter, username))

	return counter

def reindex_all(context):
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	users = context.connection.root()['nti.dataserver']['users']

	ds_intid = lsm.getUtility(provided=zope.intid.IIntIds)
	component.provideUtility(ds_intid, zope.intid.IIntIds)
	component.provideUtility(ds_intid, zc_intid.IIntIds)

	# remove all catalogs first
	for user in users.values():
		remove_entity_indices(user, include_dfls=True)

	# reindex all users ugd
	for user in users.values():
		reindex_ugd(user, users.get, ds_intid)

	logger.debug('Reindexing done!!!')
