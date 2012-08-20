#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies for the censoring of modeled content objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.contentfragments import interfaces as frg_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

from nti.contentfragments import censor


@interface.implementer( frg_interfaces.ICensoredContentPolicy )
@component.adapter( frg_interfaces.IUnicodeContentFragment, nti_interfaces.IModeledContent )
def creator_and_location_censor_policy( fragment, target ):
	"""
	Attempts to locate a censoring policy, appropriate for the creator
	of the target object and the location in which it is being created.

	.. note:: We do not really have much sense of roles yet, but when we do
		this needs to take those into account (i.e., a teacher might be able to get
		away with more than a student). Currently, we just take some broad-based
		things into account, such as user age (coppa status).

	The current policy is simple: profanity is filtered for everyone
	by replacing it with family friendly symbols. For adult users, this policy can be
	turned off in certain content units.

	The event listener works by re-dispatching based on creator and location. In effect
	it turns one sort of event dispatch into another sort. The original event dispatch
	was name-based (the adapter has to be named for the field), and this dispatcher
	needs to be registered by name. The adapters this dispatcher finds based on creator and location,
	on the other hand, SHOULD NOT be registered by name. That is implicit in the first
	dispatch.

	.. note:: This falls over when we have objects that can be edited by
		someone besides their creator. Then we would need to be checking the
		current authenticated principal instead of the creator, or the one
		that is the most restrictive, or both.


	"""

	creator = None
	location = None

	if not target.creator or not target.containerId:
		return censor.DefaultCensoredContentPolicy()

	creator = target.creator

	# TODO: It's possible this isn't doing what we want for Messages. They have
	# a containerId that is their meeting? But we actually want to use
	# the meeting's containerId?

	library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
	if library is not None:
		content_units = library.pathToNTIID( target.containerId )
		if content_units:
			location = content_units[-1]

	return component.queryMultiAdapter( (creator, location), frg_interfaces.ICensoredContentPolicy )


@interface.implementer(frg_interfaces.ICensoredContentPolicy)
@component.adapter( nti_interfaces.ICoppaUser, lib_interfaces.IContentUnit )
def coppa_user_censor_policy( user, content_unit ):
	"""
	The default profanity filter always applies to underage users.
	"""
	return censor.DefaultCensoredContentPolicy()

@interface.implementer(frg_interfaces.ICensoredContentPolicy)
@component.adapter(nti_interfaces.IUser,lib_interfaces.IDelimitedHierarchyContentUnit)
def user_filesystem_censor_policy( user, file_content_unit ):
	"""
	Profanity filtering may be turned off in specific content units
	by the use of a '.nti_disable_censoring' flag file.
	"""
	# TODO: maybe this could be handled with an ACL entry? The permission
	# to post uncensored things?
	if file_content_unit.does_sibling_entry_exist( '.nti_disable_censoring' ):
		return None
	return coppa_user_censor_policy( user, file_content_unit )
