# -*- coding: utf-8 -*-
"""
Content search generation 20.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 20

import zope.intid
from zope import component
from zc import intid as zc_intid
from ZODB.POSException import POSKeyError
from zope.component.hooks import site, setHooks

from ..common import post_
from ..utils import find_all_posts
from .. import interfaces as search_interfaces
from .. import _discriminators as discriminators
from ..utils._repoze_utils import remove_entity_catalogs

def reindex_posts(user, users_get, ds_intid):
	counter = 0
	try:
		username = user.username
		logger.debug('Reindexing posts(s) for %s' % username)
		for e, obj in find_all_posts(user, users_get):
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
				# broken reference for object
				pass

		logger.debug('%s post object(s) for user %s were reindexed' % (counter, username))
	except POSKeyError:
		# broken reference for user
		pass
	return counter

def do_evolve(context):
	"""
	Reindex posts.
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
			remove_entity_catalogs(user, (post_,))

		# reindex all users ugd
		for user in users.values():
			reindex_posts(user, users.get, ds_intid)

	logger.debug('Evolution done!!!')

def evolve(context):
	pass
