# -*- coding: utf-8 -*-
"""
Content search generation 25.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 26

import zope.intid
from zope import component
from zc import intid as zc_intid
from zope.component.hooks import site, setHooks

from ZODB.POSException import POSKeyError

from .. import _repoze_index
from ..constants import (note_, title_)
from .. import interfaces as search_interfaces

def do_evolve(context):
	"""
	Add title to the note indices
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

		for user in users.values():
			try:
				rim = search_interfaces.IRepozeEntityIndexManager(user, None)
				catalog = rim.get(note_, None)  if rim is not None else None
				if catalog is None:
					continue

				if title_ not in catalog:
					_repoze_index._title_field_creator(catalog, title_, search_interfaces.INoteRepozeCatalogFieldCreator)
					logger.debug("Title column added to note catalog for user '%s'" % user)

			except POSKeyError:
				# broken reference for user
				pass

	logger.debug('Evolution done!!!')

def evolve(context):
	"""
	Evolve generation 25 to 26 by adding a title column to note catalogs
	"""
	do_evolve(context)
