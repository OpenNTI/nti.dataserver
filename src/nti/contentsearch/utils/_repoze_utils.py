# -*- coding: utf-8 -*-
"""
Content search repoze utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from ZODB.POSException import POSKeyError

from .. import constants
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
		for catalog_name in sorted(rim.keys()):  # dependable iteration order
			catalog = rim[catalog_name]
			catalog_field_possessing_docids = None
			if catalog:
				# We cannot choose a random one of these from iterating across values()
				# the result would be undefined. Instead we try to find one we think
				# should be there
				for catalog_field_name in constants.text_fields:
					catalog_field_possessing_docids = catalog.get(catalog_field_name)
					if catalog_field_possessing_docids:
						break

			if hasattr(catalog_field_possessing_docids, "_indexed"):
				yield catalog, list(catalog_field_possessing_docids._indexed())
	except POSKeyError:
		pass
