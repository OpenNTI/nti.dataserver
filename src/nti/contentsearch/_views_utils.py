# -*- coding: utf-8 -*-
"""
View utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

import repoze.lru

from nti.ntiids import ntiids

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

@repoze.lru.lru_cache(300)
def get_ntiid_path(ntiid, registry=component):
	result = ()
	library = registry.queryUtility(IContentPackageLibrary)
	if library and ntiid and ntiids.is_valid_ntiid_string(ntiid):
		paths = library.pathToNTIID(ntiid)
		result = tuple([p.ntiid for p in paths]) if paths else ()
	return result

def get_collection(ntiid, registry=component):
	result = get_ntiid_path(ntiid, registry)
	return unicode(result[0].lower()) if result else None

def get_user_accessible_content(user, registry=component):
	
	user = users.User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	library = registry.queryUtility(IContentPackageLibrary)
	
	packages = {}
	for package in (library.contentPackages if library is not None else ()):
		provider = ntiids.get_provider( package.ntiid ).lower() 
		specific = ntiids.get_specific( package.ntiid ).lower() 
		role = nauth.role_for_providers_content( provider, specific ) 
		packages[role.id] = package.ntiid
		
	result = set()
	for x in member.groups or ():
		ntiid = packages.get(x.id, None)
		if ntiid: 
			ntiid = get_collection(ntiid, registry)
			result.add(ntiid)
	return result
