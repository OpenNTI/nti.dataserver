#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies for the censoring of modeled content objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

import six

from nti.dataserver import interfaces as nti_interfaces
from nti.contentfragments import interfaces as frg_interfaces
from nti.contentlibrary import interfaces as lib_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.socketio import interfaces as sio_interfaces

from nti.dataserver import users

from nti.contentfragments import censor

from nti.appserver import site_policies

class IObjectNotTiedToContent(interface.Interface):
	"""
	This object is used when we need to look up censoring
	policies but could not determine a (content) location.
	"""
	# TODO: Now that we have ModeledContent objects that are not in the
	# library (e.g., forums, blogs), this may need rethought. (2013-03-05)


@interface.provider(IObjectNotTiedToContent)
class ObjectNotTiedToContent(object):
	"Direct provider of IObjectNotTiedToContent"



@interface.implementer( frg_interfaces.ICensoredContentPolicy )
@component.adapter( frg_interfaces.IUnicodeContentFragment, nti_interfaces.IModeledContent )
def creator_and_location_censor_policy( fragment, target, site_names=None ):
	"""
	Attempts to locate a censoring policy, appropriate for the creator
	of the target object and the location in which it is being created.

	.. note:: We do not really have much sense of roles yet, but when
		we do this needs to take those into account (i.e., a teacher
		might be able to get away with more than a student).
		Currently, we just take some broad-based things into account,
		such as user age (coppa status).

	The current policy is simple: profanity is filtered for everyone
	by replacing it with family friendly symbols. For adult users,
	this policy can be turned off in certain content units.

	The event listener works by re-dispatching based on creator and
	location. In effect it turns one sort of event dispatch into
	another sort. The original event dispatch was name-based (the
	adapter has to be named for the field), and this dispatcher needs
	to be registered by name. The adapters this dispatcher finds based
	on creator and location, on the other hand, SHOULD NOT be
	registered by name. That is implicit in the first dispatch.

	.. note:: This falls over when we have objects that can be edited
		by someone besides their creator. Then we would need to be
		checking the current authenticated principal instead of the
		creator, or the one that is the most restrictive, or both.

	.. note:: This also slightly falls over for objects that are not contained
		within content.

	:keyword list site_names: If given, this is an ordered list of the active sites
		we should consider when looking for site-wide policies. It can
		be passed by another adapter factory that has this context information
		not dependent on the current request.

	"""

	creator = None
	location = None

	if not target.creator: # Nothing to go off of, must assume the worst
		return censor.DefaultCensoredContentPolicy()

	creator = target.creator
	__traceback_info__ = creator, target
	# Hmm Kay. If we find a string for a creator, try to resolve
	# it to an entity.
	if isinstance( creator, six.string_types ):
		creator = users.Entity.get_entity( username=creator, default=creator )

	# TODO: It's possible this isn't doing what we want for Messages. They have
	# a containerId that is their meeting? But we actually want to use
	# the meeting's containerId? As it is, this winds up finding a `location`
	# of ``None``, which gets matched by the * in the adapter registration

	if target.containerId:
		# Try to find a location to put it in.
		# See comments above about how this is starting to not be appropriate.
		library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
		content_units = library.pathToNTIID( target.containerId ) if library is not None else None
		location = content_units[-1] if content_units else None

	if location is None:
		location = ObjectNotTiedToContent

	# In general the site_policies.queryMulitAdapterInSite is deprecated,
	# but its currently here for chat messages. (See below). This can
	# probably go away once tests are updated
	return site_policies.queryMultiAdapterInSite( (creator, location),
												  frg_interfaces.ICensoredContentPolicy,
												  site_names=site_names	)


@interface.implementer(frg_interfaces.ICensoredContentPolicy)
@component.adapter( nti_interfaces.ICoppaUser, interface.Interface )
def coppa_user_censor_policy( user, content_unit ):
	"""
	The default profanity filter always applies to underage users,
	no matter where they attempt to do something (IContentUnit
	or IObjectNotTiedToContent).
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
	return censor.DefaultCensoredContentPolicy()

###
# TODO: The copying of site names below is probably no longer
# necessary. While this still happen outside of a request,
# the transaction runner is establishing the proper context
# for a site in the ZCA hierarchy automatically. However,
# it also doesn't hurt anything so it can stay until a test
# is written to prove it.
###

@component.adapter( chat_interfaces.IMessageInfo, sio_interfaces.ISocketSessionCreatedObjectEvent )
def ensure_message_info_has_creator( message, event ):
	"""
	Ensures that messages created by sockets have their creator set immediately. This is necessary
	to be sure that the correct security and censoring policies are applied.

	We also copy the originating site names from the session if they exist into a temporary
	attribute.
	"""
	# Recall that sessions have string as their owner,
	# and messages keep it that way
	message.creator = event.session.owner
	setattr( message, '_v_originating_site_names',
			 getattr(event.session, 'originating_site_names', () ) )

@interface.implementer( frg_interfaces.ICensoredContentPolicy )
@component.adapter(frg_interfaces.IUnicodeContentFragment, chat_interfaces.IMessageInfo )
def message_info_uses_captured_session_info( fragment, target ):
	"""
	Chat messages usually arrive outside an active request. So we use the sites
	that originated the session, which we captured on the session itself
	and then copied to the message.
	"""

	return creator_and_location_censor_policy( fragment, target, site_names=getattr( target, '_v_originating_site_names', () ) )
