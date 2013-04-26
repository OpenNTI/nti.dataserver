# -*- coding: utf-8 -*-
"""
Store content role management.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver.users import User
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

def _get_collection_root(library, ntiid):
	result = None
	if library and ntiid:
		paths = library.pathToNTIID(ntiid)
		result = paths[0] if paths else None
	return result

def _get_descendants(unit):
	yield unit
	last = unit
	for node in _get_descendants(unit):
		for child in node.children:
			yield child
			last = child
		if last == node:
			return

def _get_collection(library, ntiid):
	croot = _get_collection_root(library, ntiid)
	result = croot.ntiid.lower() if croot else None
	return result

def _add_users_content_roles( user, items ):
	"""
	Add the content roles to the given user

	:param user: The user object
	:param items: List of ntiids
	"""
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	if not user or not items:
		return 0
	
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	
	roles_to_add = set()
	current_roles = {x.id:x for x in member.groups}
	library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
	
	for item in items:
		item = _get_collection(library, item) if item and ntiids.is_valid_ntiid_string(item) else None
		if item is None:
			continue
		
		provider = ntiids.get_provider(item).lower()
		specific = ntiids.get_specific(item).lower()
		role = nauth.role_for_providers_content(provider, specific)
		if role.id not in current_roles:
			logger.info("Role %s added to %s", role.id, user)
			roles_to_add.add(role)
	
	member.setGroups( list(current_roles.values()) + list(roles_to_add) )
	return len(roles_to_add)

def _remove_users_content_roles( user, items ):
	"""
	Remove the content roles from the given user

	:param user: The user object
	:param items: List of ntiids
	"""
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	if not user or not items:
		return 0
	
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	if not member.hasGroups():
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
			role = nauth.role_for_providers_content(provider, specific)
			roles_to_remove.add(role.id)

	for r in roles_to_remove:
		if current_roles.pop(r, None):
			logger.info("Role %s removed from %s", r, user)
	
	member.setGroups( list(current_roles.values()) )
	return current_size - len(current_roles)

def _get_users_content_roles( user ):
	"""
	Return a list of tuples with the user content roles 

	:param user: The user object
	"""
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	
	result = []
	for x in member.groups or ():
		if x.id.startswith(nauth.CONTENT_ROLE_PREFIX):
			spl = x.id[len(nauth.CONTENT_ROLE_PREFIX):].split(':')
			if len(spl) >= 2: 
				result.append((spl[0], spl[1]))
	return result
