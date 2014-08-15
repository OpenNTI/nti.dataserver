#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re

import datetime
import operator

from zope import component
from zope import interface
from zope import lifecycleevent
from zope.event import notify
from zope.container.interfaces import INameChooser

from ZODB.interfaces import IConnection

from pyramid.view import view_config
from pyramid.view import view_defaults  # NOTE: Only usable on classes
from pyramid import httpexceptions as hexc

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.utils._compat import aq_base

from nti.appserver.traversal import find_interface

from nti.app.base.abstract_views import AuthenticatedViewMixin
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.appserver.ugd_query_views import Operator
from nti.appserver.ugd_edit_views import UGDPutView
from nti.appserver.ugd_edit_views import UGDDeleteView
from nti.appserver.ugd_feed_views import AbstractFeedView
from nti.appserver.ugd_query_views import _combine_predicate
from nti.appserver.ugd_query_views import _UGDView as UGDQueryView
from nti.appserver.dataserver_pyramid_views import _GenericGetView as GenericGetView

from nti.dataserver import authorization as nauth

from nti.dataserver import interfaces as nti_interfaces
from nti.app.renderers import interfaces as app_renderers_interfaces

from nti.contentprocessing import content_utils
from nti.contentsearch import interfaces as search_interfaces

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.dataserver.contenttypes.forums.post import Post
from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.forum import ACLCommunityForum
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
from nti.dataserver.contenttypes.forums.post import GeneralForumComment
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.post import CommunityHeadlinePost
from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

from nti.externalization.interfaces import StandardExternalFields

from .. import VIEW_CONTENTS
from nti.appserver.pyramid_authorization import is_readable

class PostUploadMixin(AuthenticatedViewMixin,
					  ModeledContentUploadRequestUtilsMixin):
	"""
	Support for uploading of IPost objects.
	"""

	_constraint = frm_interfaces.IPost.providedBy

	_override_content_type = None
	#: Set to a non-empty sequence to require one of a particular type. The `_override_content_type`
	#: is only applied if the incoming type is in the sequence; you must have a valid
	#: `_constraint` in that case to protect against other incoming types.
	#: Set to None to always use the _override_content_type (forcing parsing the incoming data
	#: as that type no matter what)
	_allowed_content_types = ()

	def _transformContentType( self, contenttype ):
		if self._override_content_type:
			if self._allowed_content_types is None:
				contenttype = self._override_content_type
			elif contenttype in self._allowed_content_types:
				contenttype = self._override_content_type
		return contenttype

	def _read_incoming_post( self ):
		# Note the similarity to ugd_edit_views
		creator = self.getRemoteUser()
		externalValue = self.readInput()
		datatype = self.findContentType( externalValue )
		tx_datatype = self._transformContentType( datatype )
		if tx_datatype is not datatype:
			datatype = tx_datatype
			if '/' in datatype:
				externalValue[StandardExternalFields.MIMETYPE] = datatype
			else:
				externalValue[StandardExternalFields.CLASS] = datatype

		containedObject = self.createAndCheckContentObject( creator, datatype, externalValue, creator, self._constraint )
		containedObject.creator = creator

		# The process of updating may need to index and create KeyReferences
		# so we need to have a jar. We don't have a parent to inherit from just yet
		# (If we try to set the wrong one, it messes with some events and some
		# KeyError detection in the containers)
		#containedObject.__parent__ = owner
		owner_jar = IConnection( self.request.context )
		if owner_jar and getattr( containedObject, '_p_jar', self) is None:
			owner_jar.add( containedObject )

		# Update the object, but don't fire any modified events. We don't know
		# if we'll keep this object yet, and we haven't fired a created event
		self.updateContentObject( containedObject, externalValue, set_id=False, notify=False )
		# Which just verified the validity of the title.

		return containedObject, externalValue

class _AbstractForumPostView(PostUploadMixin,
							 AbstractAuthenticatedView):
	""" Given an incoming IPost, creates a new container in the context. """

	@property
	def _allowed_content_types(self):
		return ('Post', Post.mimeType, 'Posts' )
	_factory = None

	def _constructor(self, external_value=None):
		return self._factory()

	def _get_topic_creator( self ):
		return self.getRemoteUser()

	def _do_call( self ):
		forum = self.request.context
		topic_post, external_value = self._read_incoming_post()

		# Now the topic
		topic = self._constructor(external_value)
		topic.creator = self._get_topic_creator()

		# Business rule: titles of the personal blog entry match the post
		topic.title = topic_post.title
		topic.description = external_value.get( 'description', topic.title )

		# For these, the name matters. We want it to be as pretty as we can get
		# TODO: We probably need to register an IReservedNames that forbids
		# _VIEW_CONTENTS and maybe some other stuff

		name = INameChooser(forum).chooseName(topic.title, topic)

		lifecycleevent.created( topic )
		forum[name] = topic # Now store the topic and fire lifecycleevent.added
		assert topic.id == name
		assert topic.containerId == forum.NTIID

		if interface.providedBy( topic ).get('headline'):
			# not all containers have headlines; those that don't simply use
			# the incoming post as a template
			topic_post.__parent__ = topic # must set __parent__ first for acquisition to work

			topic_post.creator = topic.creator

			# In order to meet the validity requirements, we must work from the root down,
			# only assigning the sublocation once the parent location is fully valid
			# (otherwise we get schema validation errors)...
			topic.headline = topic_post

			# ...this means, however, that the initial ObjectAddedEvent did not get fired
			# for the headline post (since it just now became a sublocation) so we must do
			# it manually
			lifecycleevent.created( topic_post )
			lifecycleevent.added( topic_post )

		# Respond with the pretty location of the object, within the blog
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( topic )

		return topic

# We allow POSTing comments/topics/forums to the actual objects, and also
# to the /contents sub-URL (ignoring anything subpath after it)
# This lets a HTTP client do a better job of caching, by
# auto-invalidating after its own comment creation
# (Of course this has the side-problem of not invalidating
# a cache of the topic object itself...)


class AbstractBoardPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new forum in the board """

	# Still read the incoming IPost-like thing, but we discard it since our "topic" (aka forum)
	# does not have a headline
	_factory = None

	#: We always override the incoming content type and parse simply as an IPost.
	#: All we care about is topic and description.
	_allowed_content_types = None
	@property
	def _override_content_type(self):
		return Post.mimeType

	_forum_factory = None

	def _constructor(self, external_value=None):
		return self._forum_factory()




class _AbstractTopicPostView(PostUploadMixin,
							 AbstractAuthenticatedView):

	@property
	def _allowed_content_types(self):
		return ('Post', Post.mimeType, 'Posts')

	def _do_call( self ):
		incoming_post, _ = self._read_incoming_post()

		topic = self.request.context

		# The actual name of these isn't tremendously important
		name = topic.generateId( prefix='comment' )

		lifecycleevent.created( incoming_post )
		# incoming_post.id and containerId are set automatically when it is added
		# to the container (but note that the created event did not have them)
		topic[name] = incoming_post # Now store the topic and fire IObjectAddedEvent (subtype of IObjectModifiedEvent)

		# Respond with the pretty location of the object
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( incoming_post )

		return incoming_post
