#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies for the censoring of modeled content objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface

from pyramid.traversal import find_interface

from nti.app.authentication import get_remote_user

from nti.appserver.interfaces import INTIIDRootResolver

from nti.appserver.policies import site_policies

from nti.chatserver.interfaces import IMessageInfo

from nti.contentfragments import censor

from nti.contentfragments.interfaces import ICensoredContentPolicy
from nti.contentfragments.interfaces import IUnicodeContentFragment

from nti.contentlibrary.interfaces import IDelimitedHierarchyContentUnit

from nti.dataserver.users import Entity
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUser

from nti.socketio.interfaces import ISocketSessionCreatedObjectEvent

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

# No default adapter list, too many things.
@interface.implementer(ICensoredContentPolicy)
def creator_and_location_censor_policy(fragment, target, site_names=None):
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

	.. note:: The creator is found either as an attribute on the `target`,
		or, failing that, in the lineage of the object. Finally failing
		that, we check for the currently active user.

	.. note:: This falls over when we have objects that can be edited
		by someone besides their creator. Then we would need to be
		checking the current authenticated principal instead of the
		creator, or the one that is the most restrictive, or both.

	.. note:: This also slightly falls over for objects that are not contained
		within content. For those, we dispatch based on the __parent__ if it
		is not None.

	:keyword list site_names: If given, this is an ordered list of the active sites
		we should consider when looking for site-wide policies. It can
		be passed by another adapter factory that has this context information
		not dependent on the current request.

	"""

	creator = getattr(target, 'creator', None)
	location = None

	if not creator:
		# Ok, try to find something in the lineage
		creator = find_interface(target, IUser)

	if not creator:
		creator = get_remote_user()

	if not creator:
		creator = getattr(target, 'username', None)  # sometimes this is an alias

	if not creator:  # Nothing to go off of, must assume the worst
		return censor.DefaultCensoredContentPolicy()

	__traceback_info__ = creator, target
	# Hmm Kay. If we find a string for a creator, try to resolve
	# it to an entity.
	if isinstance(creator, six.string_types):
		creator = Entity.get_entity(username=creator, default=creator)

	# TODO: It's possible this isn't doing what we want for Messages. They have
	# a containerId that is their meeting? But we actually want to use
	# the meeting's containerId? As it is, this winds up finding a `location`
	# of ``None``, which gets matched by the * in the adapter registration

	if getattr(target, 'containerId', None):
		# Try to find a location to put it in.
		# See comments above about how this is starting to not be appropriate.
		resolver = component.queryUtility(INTIIDRootResolver)
		location = resolver.resolve(target.containerId) if resolver else None

	if location is None:
		location = getattr(target, '__parent__', None)

	if location is None:
		location = ObjectNotTiedToContent

	# In general the site_policies.queryMulitAdapterInSite is deprecated,
	# but its currently here for chat messages. (See below). This can
	# probably go away once tests are updated
	return site_policies.queryMultiAdapterInSite((creator, location),
												  ICensoredContentPolicy,
												  site_names=site_names)

@interface.implementer(ICensoredContentPolicy)
@component.adapter(ICoppaUser, interface.Interface)
def coppa_user_censor_policy(user, content_unit):
	"""
	The default profanity filter always applies to underage users,
	no matter where they attempt to do something (IContentUnit
	or IObjectNotTiedToContent).
	"""
	return censor.DefaultCensoredContentPolicy()

@interface.implementer(ICensoredContentPolicy)
@component.adapter(IUser, IDelimitedHierarchyContentUnit)
def user_filesystem_censor_policy(user, file_content_unit):
	"""
	Profanity filtering may be turned off in specific content units
	by the use of a '.nti_disable_censoring' flag file.
	"""
	# TODO: maybe this could be handled with an ACL entry? The permission
	# to post uncensored things?

	if file_content_unit.does_sibling_entry_exist('.nti_disable_censoring'):
		return None
	return censor.DefaultCensoredContentPolicy()

# ##
# TODO: The copying of site names below is probably no longer
# necessary. While this still happen outside of a request,
# the transaction runner is establishing the proper context
# for a site in the ZCA hierarchy automatically. However,
# it also doesn't hurt anything so it can stay until a test
# is written to prove it.
# ##

@component.adapter(IMessageInfo, ISocketSessionCreatedObjectEvent)
def ensure_message_info_has_creator(message, event):
	"""
	Ensures that messages created by sockets have their creator set immediately. This is necessary
	to be sure that the correct security and censoring policies are applied.

	We also copy the originating site names from the session if they exist into a temporary
	attribute.
	"""
	# Recall that sessions have string as their owner,
	# and messages keep it that way
	message.creator = event.session.owner
	setattr(message, '_v_originating_site_names',
			getattr(event.session, 'originating_site_names', ()))

@interface.implementer(ICensoredContentPolicy)
@component.adapter(IUnicodeContentFragment, IMessageInfo)
def message_info_uses_captured_session_info(fragment, target):
	"""
	Chat messages usually arrive outside an active request. So we use the sites
	that originated the session, which we captured on the session itself
	and then copied to the message.
	"""
	site_names = getattr(target, '_v_originating_site_names', ())
	return creator_and_location_censor_policy(fragment,
											  target, 
											  site_names=site_names)
