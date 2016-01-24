#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 71

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.recorder.record import copy_records

from nti.recorder.index import get_recordables
from nti.recorder.index import install_recorder_catalog

from nti.recorder.interfaces import TRX_RECORD_HISTORY_KEY

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert  component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		lsm = ds_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)

		catalog = install_recorder_catalog(ds_folder, intids)
		recordables = get_recordables(catalog=catalog, intids=intids)
		for recordable in recordables:
			try:
				anno = recordable.__annotations__
				old = anno.get(TRX_RECORD_HISTORY_KEY, None)
				if not old or not hasattr(old, '_records'):
					continue
				# remove old storage
				anno.pop(TRX_RECORD_HISTORY_KEY, None)
				locate(old, None, None)
				copy_records(recordable, old._records)
			except AttributeError:
				pass
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 71 by migrating transaction history storage
	"""
	do_evolve(context)
