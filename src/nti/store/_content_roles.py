# -*- coding: utf-8 -*-

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
	Update the content roles assigned to the given user based on content ntiids 

	:param user: The user object
	:param items: List of ntiids the user will be given access to
	"""
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	if not items and not member.hasGroups():
		return 0
	
	roles_to_add = []
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
			roles_to_add.append(role_id)
	
	member.setGroups( list(current_roles.values()) + roles_to_add )
	return len(roles_to_add)
