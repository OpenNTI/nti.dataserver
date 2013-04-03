#!/usr/bin/env python
"""zope.generations installer for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 0

from zope.generations.generations import SchemaManager

class _StoreSchemaManager(SchemaManager):
	"""
	A schema manager that we can register as a utility in ZCML.
	"""
	def __init__(self):
		super(_StoreSchemaManager, self).__init__(generation=generation,
												  minimum_generation=generation,
												  package_name='nti.store.generations')



import zope.intid

from .. import interfaces as store_interfaces
from ..purchasable_store import PurchasableStore

def evolve(context):
	result = install_store(context)
	return result

def install_store(context):
	conn = context.connection
	root = conn.root()
	dataserver_folder = root['nti.dataserver']

	# create store
	store = PurchasableStore()
	store.__name__ = '++etc++store'
	store.__parent__ = dataserver_folder

	lsm = dataserver_folder.getSiteManager()
	lsm.registerUtility(store, provided=store_interfaces.IPurchasableStore)

	ds_intid = lsm.getUtility(zope.intid.IIntIds)
	ds_intid.register(store)

	return store
