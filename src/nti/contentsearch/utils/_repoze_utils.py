from __future__ import print_function, unicode_literals

from nti.contentsearch import get_indexable_types
from nti.contentsearch import interfaces as search_interfaces

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
	rim = search_interfaces.IRepozeEntityIndexManager(entity)
	return remove_rim_catalogs(rim, content_types)

def get_catalog_and_docids(entity):
	rim = search_interfaces.IRepozeEntityIndexManager(entity)
	for catalog in rim.values():
		catfield = list(catalog.values())[0] if catalog else None
		if hasattr(catfield, "_indexed"):
			yield catalog, list(catfield._indexed())



		