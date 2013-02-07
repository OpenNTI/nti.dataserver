# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from collections import defaultdict

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

def _get_collection(library, ntiid):
	result = None
	if library and ntiid:
		paths = library.pathToNTIID(ntiid)
		result = paths[0].ntiid.lower() if paths else None
	return result

def _add_users_content_roles( user, items ):
	"""
	Update the content roles assigned to the given user based on content ntiids 

	:param user: The user object
	:param items: List of ntiids the user will be given access to
	"""
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	if not items and not member.hasGroups():
		return 0
	
	roles_to_add = []
	other_provider_roles = set()
	provider_packages = defaultdict(set)
	
	library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
	content_packages = library.contentPackages if library is not None else ()
		
	for package in content_packages:
		pnid = package.ntiid
		provider_packages[ntiids.get_provider(pnid).lower()].add(ntiids.get_specific(pnid).lower() )
				
	for item in items:
		item = _get_collection(library, item) if item and ntiids.is_valid_ntiid_string(item) else None
		if item is None:
			continue
		
		provider = ntiids.get_provider(item).lower()
		specific = ntiids.get_specific(item).lower()
		
		empty_role = nauth.role_for_providers_content( provider, '' )
		other_provider_roles.update([x for x in member.groups if not x.id.startswith( empty_role.id )])
		
		if provider in provider_packages and specific in provider_packages[provider]:
			roles_to_add.append( nauth.role_for_providers_content( provider, specific ) )
	
	member.setGroups( list(other_provider_roles) + roles_to_add )
	
	return len(roles_to_add)
