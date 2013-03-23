# -*- coding: utf-8 -*-
"""
Content search repoze utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from ZODB.POSException import POSKeyError

from . import find_user_dfls
from .. import get_indexable_types
from .. import interfaces as search_interfaces

def remove_rim_catalogs(rim, content_types=()):
	"""remove all the repoze catalogs from the specified entity manager"""
	count = 0
	content_types = content_types if content_types else get_indexable_types()
	for key in list(rim.keys()):
		if key in content_types:
			rim.pop(key, None)
			count += 1
	return count

def remove_entity_catalogs(entity, content_types=()):
	"""remove all the repoze catalogs from the specified entity"""
	result = 0
	content_types = content_types if content_types else get_indexable_types()
	try:
		rim = search_interfaces.IRepozeEntityIndexManager(entity, None)
		result = remove_rim_catalogs(rim, content_types) if rim is not None else 0
	except POSKeyError:
		pass
	return result

def remove_entity_indices(entity, content_types=(), include_dfls=False):
	result = remove_entity_catalogs(entity, content_types)
	if include_dfls:
		for dfl in find_user_dfls(entity):
			result += remove_entity_catalogs(dfl, content_types)
	return result

def get_catalog_and_docids(entity):
	try:
		rim = search_interfaces.IRepozeEntityIndexManager(entity, {})
		for catalog_name in sorted(rim.keys()): # dependable iteration order
			catalog = rim[catalog_name]
			catfield = list(catalog.values())[0] if catalog else None
			if hasattr(catfield, "_indexed"):
				yield catalog, list(catfield._indexed())
	except POSKeyError:
		pass
