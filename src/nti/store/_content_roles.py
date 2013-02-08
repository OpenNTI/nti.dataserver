# -*- coding: utf-8 -*-
"""
Store content role management.

$Id: pyramid_views.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver.users import User
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
	Add the content roles to the given user

	:param user: The user object
	:param items: List of ntiids
	"""
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	if not items and not member.hasGroups():
		return 0
	
	roles_to_add = set()
	current_roles = {x.id:x for x in member.groups}
	library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
	
	for item in items:
		item = _get_collection(library, item) if item and ntiids.is_valid_ntiid_string(item) else None
		if item is None:
			continue
		
		provider = ntiids.get_provider(item).lower()
		specific = ntiids.get_specific(item).lower()
		role_id = nauth.role_for_providers_content( provider, specific ) 
		if role_id not in current_roles:
			roles_to_add.add(role_id)
	
	member.setGroups( list(current_roles.values()) + list(roles_to_add) )
	return len(roles_to_add)

def _remove_users_content_roles( user, items ):
	"""
	Remove the content roles from the given user

	:param user: The user object
	:param items: List of ntiids
	"""
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	if not items and not member.hasGroups():
		return 0

	roles_to_remove = set()
	current_roles = {x.id.lower():x for x in member.groups}
	library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
	current_size = len(current_roles)

	for item in items:
		item = _get_collection(library, item) if item and ntiids.is_valid_ntiid_string(item) else None
		if item:
			provider = ntiids.get_provider(item).lower()
			specific = ntiids.get_specific(item).lower()
			role_id = nauth.role_for_providers_content( provider, specific ) 
			roles_to_remove.add(role_id.id)

	for r in roles_to_remove:
		current_roles.pop(r, None)
	
	member.setGroups( list(current_roles.values()) )
	return current_size - len(current_roles)
