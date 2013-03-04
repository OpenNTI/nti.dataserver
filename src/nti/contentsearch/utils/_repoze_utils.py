# -*- coding: utf-8 -*-
"""
Content search repoze utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from ZODB.POSException import POSKeyError

from .. import get_indexable_types
from .. import interfaces as search_interfaces

def remove_rim_catalogs(rim, content_types=()):
	"""remove all the repoze catalogs from the specified entity manager"""
	content_types = content_types or get_indexable_types()
	for key in list(rim.keys()):
		if key in content_types:
			rim.pop(key, None)
	return True
			
def remove_entity_catalogs(entity, content_types=()):
	"""remove all the repoze catalogs from the specified entity"""
	content_types = content_types or get_indexable_types()
	try:
		rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
		return remove_rim_catalogs(rim, content_types) if rim is not None else False
	except POSKeyError:
		pass

def get_catalog_and_docids(entity):
	rim = search_interfaces.IRepozeEntityIndexManager(entity)
	for catalog in rim.values():
		catfield = list(catalog.values())[0] if catalog else None
		if hasattr(catfield, "_indexed"):
			yield catalog, list(catfield._indexed())
