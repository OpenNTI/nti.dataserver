#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content role management.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from zope import component

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver.users import User
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from . import content_utils

def get_user(user):
	user = 	User.get_user(str(user)) \
			if not nti_interfaces.IUser.providedBy(user) else user
	return user

def get_descendants(unit):
	yield unit
	last = unit
	for node in get_descendants(unit):
		for child in node.children:
			yield child
			last = child
		if last == node:
			return

def check_item_in_library(item, library=None, registry=component):
	item = 	content_utils.get_collection_root_ntiid(item, library=library, registry=registry) \
			if item and ntiids.is_valid_ntiid_string(item) else None
	return item

def add_content_roles(user, roles_to_add, registry=component):
	if isinstance(roles_to_add, six.string_types):
		roles_to_add = roles_to_add.split()

	member = registry.getAdapter(user, nti_interfaces.IMutableGroupMember,
								 nauth.CONTENT_ROLE_PREFIX)

	current_roles = {x.id:x for x in member.groups}
	all_roles = set(list(current_roles.values()) + list(roles_to_add))
	member.setGroups(list(all_roles))

def add_users_content_roles(user, items, library=None, registry=component):
	"""
	Add the content roles to the given user

	:param user: The user object
	:param items: List of ntiids
	"""
	user = get_user(user)
	if not user or not items:
		return 0

	member = registry.getAdapter(user, nti_interfaces.IMutableGroupMember,
								 nauth.CONTENT_ROLE_PREFIX)

	roles_to_add = set()
	current_roles = {x.id:x for x in member.groups}

	for item in items:
		item = check_item_in_library(item, library, registry)
		if item is None:
			continue

		provider = ntiids.get_provider(item).lower()
		specific = ntiids.get_specific(item).lower()
		role = nauth.role_for_providers_content(provider, specific)
		if role.id not in current_roles:
			logger.info("Role %s added to %s", role.id, user)
			roles_to_add.add(role)

	member.setGroups(list(current_roles.values()) + list(roles_to_add))
	return len(roles_to_add)

def remove_users_content_roles(user, items, library=None, registry=component):
	"""
	Remove the content roles from the given user

	:param user: The user object
	:param items: List of ntiids
	"""
	user = get_user(user)
	if not user or not items:
		return 0

	member = registry.getAdapter(user, nti_interfaces.IMutableGroupMember,
								 nauth.CONTENT_ROLE_PREFIX)
	if not member.hasGroups():
		return 0

	roles_to_remove = set()
	current_roles = {x.id.lower():x for x in member.groups}
	current_size = len(current_roles)

	for item in items:
		item = check_item_in_library(item, library, registry)
		if item:
			provider = ntiids.get_provider(item).lower()
			specific = ntiids.get_specific(item).lower()
			role = nauth.role_for_providers_content(provider, specific)
			roles_to_remove.add(role.id)

	for r in roles_to_remove:
		if current_roles.pop(r, None):
			logger.info("Role %s removed from %s", r, user)

	member.setGroups(list(current_roles.values()))
	return current_size - len(current_roles)

def get_users_content_roles(user, registry=component):
	"""
	Return a list of tuples with the user content roles 

	:param user: The user object
	"""
	user = get_user(user)
	member = registry.getAdapter(user, nti_interfaces.IMutableGroupMember,
								 nauth.CONTENT_ROLE_PREFIX)

	result = []
	for x in member.groups or ():
		if x.id.startswith(nauth.CONTENT_ROLE_PREFIX):
			spl = x.id[len(nauth.CONTENT_ROLE_PREFIX):].split(':')
			if len(spl) >= 2:
				result.append((spl[0], spl[1]))
	return result

def get_user_accessible_content(user, library=None, registry=component):
	user = get_user(user)

	member = registry.getAdapter(user, nti_interfaces.IMutableGroupMember,
								 nauth.CONTENT_ROLE_PREFIX)

	library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) \
			  if library is None else library

	packages = {}
	for package in (library.contentPackages if library is not None else ()):
		provider = ntiids.get_provider(package.ntiid).lower()
		specific = ntiids.get_specific(package.ntiid).lower()
		role = nauth.role_for_providers_content(provider, specific)
		packages[role.id] = package.ntiid

	result = set()
	for x in member.groups or ():
		ntiid = packages.get(x.id, None)
		if ntiid:
			ntiid = content_utils.get_collection_root_ntiid(ntiid, library=library,
															registry=registry)
			result.add(ntiid)
	return result
