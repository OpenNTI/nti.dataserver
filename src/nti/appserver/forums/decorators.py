#!/usr/bin/env python
"""
External decorators to provide access to the things exposed through this package.
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.utils._compat import aq_base

from nti.externalization import interfaces as ext_interfaces
from nti.dataserver.interfaces import IUser, ICommunity, IUnscopedGlobalCommunity, IDefaultPublished
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard, IForum, ITopic
from zope.container.interfaces import ILocation

from nti.appserver._util import AbstractTwoStateViewLinkDecorator
from nti.externalization.singleton import SingletonDecorator

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS

from nti.dataserver.links import Link

from .._util import link_belongs_to_user
from .._view_utils import get_remote_user

from ..pyramid_authorization import is_readable
from pyramid.threadlocal import get_current_request

from nti.dataserver.contenttypes.forums.forum import PersonalBlog
_BLOG_NAME = PersonalBlog.__default_name__

from nti.dataserver.contenttypes.forums.board import CommunityBoard
_BOARD_NAME = CommunityBoard.__default_name__

from . import VIEW_PUBLISH
from . import VIEW_UNPUBLISH
from . import VIEW_CONTENTS

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(IUser)
class BlogLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		the_links = mapping.setdefault( LINKS, [] )

		# Notice we DO NOT adapt; it must already exist, meaning that the
		# owner has at one time added content to it. It may not have published
		# content, though, and it may no longer have any entries
		# (hence 'not None' rather than __nonzero__)
		blog = context.containers.getContainer( _BLOG_NAME )
		if blog is not None and is_readable( blog ):
			link = Link( context,
						 rel=_BLOG_NAME,
						 elements=(_BLOG_NAME,) )
			link_belongs_to_user( link, context )
			the_links.append( link )

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(ICommunity)
class CommunityBoardLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		if IUnscopedGlobalCommunity.providedBy( context ):
			# The global communities that do not participate in security
			# (e.g., Everyone) do not get a forum
			return

		 # TODO: This may be slow, if the forum doesn't persistently
		 # exist and we keep creating it and throwing it away (due to
		 # not commiting on GET)
		board = ICommunityBoard( context, None )
		if board is not None: # Not checking security. If the community is visible to you, the forum is too
			the_links = mapping.setdefault( LINKS, [] )
			link = Link( context,
						 rel=_BOARD_NAME,
						 elements=(_BOARD_NAME,) )
			link_belongs_to_user( link, context )
			the_links.append( link )

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class PublishLinkDecorator(AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate publish or unpublish link
	"""
	false_view = VIEW_PUBLISH
	true_view = VIEW_UNPUBLISH

	def predicate( self, context, current_username ):
		if IDefaultPublished.providedBy( context ):
			return True

	def decorateExternalMapping( self, context, mapping ):
		# Only for the owner
		current_user = get_remote_user( get_current_request() )
		if not current_user or current_user != context.creator:
			return
		super(PublishLinkDecorator,self).decorateExternalMapping( context, mapping )


# Notice we do not declare what we adapt--we adapt too many things
# that share no common ancestor. (We could be declared on IContainer,
# but its not clear what if any IContainers we externalize besides
# the forum objects)
from nti.appserver.pyramid_renderers import md5_etag, _get_remote_username

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class ForumObjectContentsLinkProvider(object):
	"""
	Decorate forum object externalizations with a link pointing to their
	children (the contents).
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		# We only do this for parented objects. Otherwise, we won't
		# be able to render the links. A non-parented object is usually
		# a weakref to an object that has been left around
		# in somebody's stream.
		# All forum objects should have fully traversable paths by themself,
		# without considering acquired info (NTIIDs from the User would mess
		# up rendering)
		context = aq_base( context )
		if not context.__parent__: # pragma: no cover
			logger.warn( "No parent; failing to add %s link to %s", VIEW_CONTENTS, context )
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
		elements=(VIEW_CONTENTS, md5_etag(context.lastModified, _get_remote_username()).replace('/','_'))
		_links = mapping.setdefault( LINKS, [] )
		for rel in VIEW_CONTENTS, 'add':
			link = Link( context, rel=rel, elements=elements )
			interface.alsoProvides( link, ILocation )
			link.__name__ = ''
			link.__parent__ = context
			_links.append( link )

		# The last link is the add link; we want to be specific about its method
		link.method = 'POST'

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
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

	def decorateExternalObject( self, context, mapping ):
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
		need_replacement_descendant = _newest_descendant is not None and not is_readable(_newest_descendant,request)
		for x in context.values():
			if is_readable(x,request):
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
