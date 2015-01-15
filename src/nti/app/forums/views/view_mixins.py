#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope import lifecycleevent
from zope.container.interfaces import INameChooser

from ZODB.interfaces import IConnection

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.base.abstract_views import AuthenticatedViewMixin
from nti.app.base.abstract_views import AbstractAuthenticatedView

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums.interfaces import IPost

from nti.externalization.interfaces import StandardExternalFields

class PostUploadMixin(AuthenticatedViewMixin,
					  ModeledContentUploadRequestUtilsMixin):
	"""
	Support for uploading of IPost objects.
	"""

	def _read_incoming_post( self, datatype, constraint ):

		# Note the similarity to ugd_edit_views
		creator = self.getRemoteUser()
		externalValue = self.readInput()

		if '/' in datatype:
			externalValue[StandardExternalFields.MIMETYPE] = datatype
		else:
			externalValue[StandardExternalFields.CLASS] = datatype

		containedObject = self.createAndCheckContentObject( creator, datatype,
															externalValue, creator,
															constraint )
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
		self.updateContentObject(containedObject, externalValue, set_id=False,
								 notify=False )
		# Which just verified the validity of the title.

		return containedObject, externalValue

	def _find_factory_from_precondition(self, forum):
		provided_by_forum = interface.providedBy(forum)
		forum_container_precondition = provided_by_forum.get('__setitem__').getTaggedValue('precondition')
		
		topic_types = forum_container_precondition.types
		assert len(topic_types) == 1
		topic_type = topic_types[0]
		
		topic_factories = list(component.getFactoriesFor(topic_type))
		if len(topic_factories) == 1:
			topic_factory_name, topic_factory = topic_factories[0]
		else:
			# nuts. ok, if we can find *exactly* what we're looking for
			# as the most-derived thing implemented by a factory, that's
			# what we take
			found = False
			for topic_factory_name, topic_factory in topic_factories:
				if list(topic_factory.getInterfaces().flattened())[0] == topic_type:
					found = True
					break
			assert found, "Programming error: ambiguous types"

		return topic_factory_name, topic_factory, topic_type

class _AbstractForumPostView(PostUploadMixin,
							 AbstractAuthenticatedView):
	""" 
	Given an incoming IPost, creates a new container in the context. 
	"""

	def _get_topic_creator( self ):
		return self.getRemoteUser()

	def _do_call( self ):
		forum = self.request.context
		_, topic_factory, _ = self._find_factory_from_precondition(forum)
		topic_type = topic_factory.getInterfaces()

		headline_field = topic_type.get('headline')
		headline_mimetype = None
		headline_constraint = IPost.providedBy
		if headline_field:
			headline_iface = headline_field.schema
			headline_constraint = headline_iface.providedBy
			headline_factories = list(component.getFactoriesFor(headline_iface))
			headline_mimetype = headline_factories[0][0]
		else:
			headline_mimetype = 'application/vnd.nextthought.forums.post'

		topic_post, external_value = self._read_incoming_post(headline_mimetype,
															  headline_constraint)

		# Now the topic
		topic = topic_factory()
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
		assert topic.__parent__ == forum
		assert topic.containerId == forum.NTIID
		
		if headline_field:
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
			
			# fail hard if no parent is set
			assert topic_post.__parent__ == topic
		
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
	""" 
	Given an incoming IPost, creates a new forum in the board 
	"""

class _AbstractTopicPostView(PostUploadMixin,
							 AbstractAuthenticatedView):

	def _do_call( self ):
		topic = self.request.context
		comment_factory_name, _, comment_iface = \
						self._find_factory_from_precondition(topic)

		incoming_post, _ = self._read_incoming_post(comment_factory_name,
													comment_iface.providedBy)

		# The actual name of these isn't tremendously important
		name = topic.generateId( prefix='comment' )

		lifecycleevent.created( incoming_post )
		# incoming_post.id and containerId are set automatically when it is added
		# to the container (but note that the created event did not have them)
		# Now store the topic and fire IObjectAddedEvent (subtype of IObjectModifiedEvent)
		topic[name] = incoming_post 
	
		# fail hard if no parent is set
		assert incoming_post.__parent__ == topic
		
		# Respond with the pretty location of the object
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( incoming_post )

		return incoming_post
