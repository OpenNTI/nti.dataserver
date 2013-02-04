from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

import repoze.lru

from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.contentlibrary.interfaces import IContentPackageLibrary

@repoze.lru.lru_cache(300)
def get_ntiid_path(ntiid, registry=component):
	result = ()
	_library = registry.queryUtility(IContentPackageLibrary)
	if _library and ntiid and is_valid_ntiid_string(ntiid):
		paths = _library.pathToNTIID(ntiid)
		result = tuple([p.ntiid for p in paths]) if paths else ()
	return result

def get_collection(ntiid, registry=component):
	result = get_ntiid_path(ntiid, registry)
	return unicode(result[0].lower()) if result else None
