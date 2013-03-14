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
	count = 0
	content_types = content_types or get_indexable_types()
	for key in list(rim.keys()):
		if key in content_types:
			rim.pop(key, None)
			count += 1
	return count

def remove_entity_catalogs(entity, content_types=()):
	"""remove all the repoze catalogs from the specified entity"""
	result = 0
	content_types = content_types or get_indexable_types()
	try:
		rim = search_interfaces.IRepozeEntityIndexManager(entity)
		result = remove_rim_catalogs(rim, content_types)
	except POSKeyError:
		pass
	return result

def get_catalog_and_docids(entity):
	rim = search_interfaces.IRepozeEntityIndexManager(entity)
	for catalog in rim.values():
		catfield = list(catalog.values())[0] if catalog else None
		if hasattr(catfield, "_indexed"):
			yield catalog, list(catfield._indexed())
