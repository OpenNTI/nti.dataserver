#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External decorators to provide access to the things exposed through this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.container.interfaces import ILocation

from pyramid.threadlocal import get_current_request

from nti.app.authentication import get_remote_user

from nti.app.publishing import VIEW_PUBLISH
from nti.app.publishing import VIEW_UNPUBLISH

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator

from nti.appserver._util import link_belongs_to_user

from nti.appserver.pyramid_authorization import can_create
from nti.appserver.pyramid_authorization import is_readable

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDefaultPublished
from nti.dataserver.interfaces import IUnscopedGlobalCommunity
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.contenttypes.forums.board import DEFAULT_BOARD_NAME
from nti.dataserver.contenttypes.forums.forum import DEFAULT_PERSONAL_BLOG_NAME

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

from nti.utils._compat import aq_base

from . import VIEW_CONTENTS

LINKS = StandardExternalFields.LINKS

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class BlogLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		the_links = mapping.setdefault(LINKS, [])
		# Notice we DO NOT adapt; it must already exist, meaning that the
		# owner has at one time added content to it. It may not have published
		# content, though, and it may no longer have any entries
		# (hence 'not None' rather than __nonzero__)
		blog = context.containers.getContainer(DEFAULT_PERSONAL_BLOG_NAME)
		if blog is not None and is_readable(blog):
			link = Link(context,
						rel=DEFAULT_PERSONAL_BLOG_NAME,
						elements=(DEFAULT_PERSONAL_BLOG_NAME,))
			link_belongs_to_user(link, context)
			the_links.append(link)

@component.adapter(ICommunity)
@interface.implementer(IExternalMappingDecorator)
class CommunityBoardLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		if IUnscopedGlobalCommunity.providedBy(context):
			# The global communities that do not participate in security
			# (e.g., Everyone) do not get a forum
			return

		# TODO: This may be slow, if the forum doesn't persistently
		# exist and we keep creating it and throwing it away (due to
		# not commiting on GET)
		board = ICommunityBoard(context, None)
		# Not checking security. If the community is visible to you, the forum is too
		if board is not None:
			the_links = mapping.setdefault(LINKS, [])
			link = Link(context,
						rel=DEFAULT_BOARD_NAME,
						elements=(DEFAULT_BOARD_NAME,))
			link_belongs_to_user(link, context)
			the_links.append(link)

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IDynamicSharingTargetFriendsList)
class DFLBoardLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		board = IDFLBoard(context, None)
		if board is not None:  # Not checking security.
			the_links = mapping.setdefault(LINKS, [])
			link = Link(context,
						rel=DEFAULT_BOARD_NAME,
						elements=(DEFAULT_BOARD_NAME,))
			link_belongs_to_user(link, context)
			the_links.append(link)

@interface.implementer(IExternalMappingDecorator)
class PublishLinkDecorator(AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate publish or unpublish link for the owner
	of the object.

	Also, because that information is useful to have for others to
	which the post is visible (for cases where additional permissions
	beyond default published are in use; in that case, visibility
	doesn't necessarily imply publication), we also provide a
	``PublicationState`` containing one of the values
	``DefaultPublished`` or null.
	"""
	false_view = VIEW_PUBLISH
	true_view = VIEW_UNPUBLISH

	def link_predicate(self, context, current_username):
		return IDefaultPublished.providedBy(context)

	def _do_decorate_external_link(self, context, mapping, extra_elements=()):
		# The owner is the only one that gets the links
		current_user = self.remoteUser
		if current_user and current_user == context.creator:
			super(PublishLinkDecorator, self)._do_decorate_external_link(context, mapping)

	def _do_decorate_external(self, context, mapping):
		super(PublishLinkDecorator, self)._do_decorate_external(context, mapping)
		# Everyone gets the status
		mapping['PublicationState'] = 'DefaultPublished' \
									  if IDefaultPublished.providedBy(context) else None

# Notice we do not declare what we adapt--we adapt too many things
# that share no common ancestor. (We could be declared on IContainer,
# but its not clear what if any IContainers we externalize besides
# the forum objects)
from nti.app.renderers.caching import md5_etag

@interface.implementer(IExternalMappingDecorator)
class ForumObjectContentsLinkProvider(object):
	"""
	Decorate forum object externalizations with a link pointing to their
	children (the contents).
	"""

	__metaclass__ = SingletonDecorator

	@classmethod
	def add_link(cls, rel, context, mapping, request, elements=None):
		_links = mapping.setdefault(LINKS, [])
		elements = elements or (VIEW_CONTENTS,
								md5_etag(context.lastModified,
										 request.authenticated_userid).replace('/', '_'))
		link = Link(context, rel=rel, elements=elements)
		interface.alsoProvides(link, ILocation)
		link.__name__ = ''
		link.__parent__ = context
		_links.append(link)
		return link

	def decorateExternalMapping(self, context, mapping):
		request = get_current_request()
		if request is None or not request.authenticated_userid:
			return

		# We only do this for parented objects. Otherwise, we won't
		# be able to render the links. A non-parented object is usually
		# a weakref to an object that has been left around
		# in somebody's stream.
		# All forum objects should have fully traversable paths by themself,
		# without considering acquired info (NTIIDs from the User would mess
		# up rendering)
		context = aq_base(context)
		if context.__parent__ is None:  # pragma: no cover
			return

		# TODO: This can be generalized by using the component
		# registry in the same way Pyramid itself does. With a lookup like
		#   adapters.lookupAll( (IViewClassifier, request.request_iface, context_iface), IView )
		# you get back a list of (name, view) pairs that are applicable.
		# ISecuredViews (which include IMultiViews) have a __permitted__ that checks ACLs;
		# if it doesn't pass then that one is obviously filtered out. IMultiViews have a
		# match and __permitted__ method, __permitted__ using match(). The main
		# trouble is filtering out the general views (i.e., those that don't specify an interface)
		# that we don't want to return for everything

		# /path/to/forum/topic/contents --> note that contents is not an @@ view,
		# simply named. This is prettier, but if we need to we can easily @@ it
		# We also include a "ETag" in the URL to facilitate caching, different everytime
		# our children change.
		# This works because everytime one of the context's children is modified,
		# our timestamp is also modified. We include the user asking just to be safe
		# We also advertise that you can POST new items to this url, which is good for caching
		elements = (VIEW_CONTENTS, md5_etag(context.lastModified,
											request.authenticated_userid).replace('/', '_'))
		self.add_link(VIEW_CONTENTS, context, mapping, request, elements)

		current_user = get_remote_user(get_current_request())
		is_coppa = ICoppaUserWithoutAgreement.providedBy(current_user)

		# Check the create permission in the forum acl.
		# FIXME: We shouldn't need to specifically check is_coppa like this.
		# That should either be handled by the ACL or, failing that,
		# by the content vocabulary
		if request is None or (not is_coppa and can_create(context, request)):
			link = self.add_link('add', context, mapping, request, elements)
			link.method = 'POST'

@interface.implementer(IExternalObjectDecorator)
@component.adapter(IForum)
class SecurityAwareForumTopicCountDecorator(object):
	"""
	Adjust the reported ``TopicCount`` to reflect publication status/security.

	.. note:: This is not scalable, as instead of using the cached
		BTree length it requires loading all of the btree nodes
		and the data in order to security check each one. Something
		will have to be done about this. We rationalize its existence
		now by assuming our other scalability problems are worse and we'll
		have to fix them all eventually; this won't be an issue in the short term.

	Also adjusts the ``NewestDescendant`` field for the same reason, setting it to
	``None`` if it shouldn't be visible. This is something of a worse hack
	as there is not a fallback object to put in its place (that would require searching
	all topic posts, which I'm not willing to do); since we are already
	walking through topics, we simply through the newest topic there. However,
	sorting is still based on the newest descendant, whatever it may be. In
	real world practice, this is unlikely to be either noticed (if there is *any*
	posting activity at all as there will almost always be a newer comment)
	or a problem. (To minimize this, we use the ``lastModified`` time of the topic,
	not its created time to determine what to fill in.)
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, context, mapping):
		if not mapping['TopicCount']:
			# Nothing to do if its already empty
			return

		request = get_current_request()
		i = 0
		newest_topic = None
		newest_topic_time = -1.0

		# We search if it's anything provided by the newest
		# descendant that's not visible; the case of a private
		# newest comment only occurs when a person has commented
		# within their own unpublished topic and is not worth
		# worrying about.
		# (TODO: Do we need to aq wrap this?)
		_newest_descendant = context.NewestDescendant
		need_replacement_descendant = _newest_descendant is not None and \
									  not is_readable(_newest_descendant, request)
		for x in context.values():
			if is_readable(x, request):
				i += 1
				if need_replacement_descendant and x.lastModified > newest_topic_time:
					newest_topic = x
					newest_topic_time = x.lastModified
		mapping['TopicCount'] = i

		if need_replacement_descendant:
			mapping['NewestDescendant'] = None
			if newest_topic is not None:
				mapping['NewestDescendant'] = newest_topic
				mapping['NewestDescendantCreatedTime'] = newest_topic.createdTime

@interface.implementer(IExternalObjectDecorator)
@component.adapter(ICommunityBoard)
class SecurityAwareBoardForumCountDecorator(object):
	"""
	Adjust the reported ``ForumCount`` to reflect publication status/security.

	.. note:: This is not scalable, as instead of using the cached
		BTree length it requires loading all of the btree nodes
		and the data in order to security check each one. Something
		will have to be done about this. We rationalize its existence
		now by assuming our other scalability problems are worse and we'll
		have to fix them all eventually; this won't be an issue in the short term.

	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, context, mapping):
		if not mapping['ForumCount']:
			# Nothing to do if its already empty
			return

		i = 0
		request = get_current_request()
		for x in context.values():
			if is_readable(x, request):
				i += 1
		mapping['ForumCount'] = i
