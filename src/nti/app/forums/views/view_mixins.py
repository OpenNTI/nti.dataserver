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

from nti.app.base.abstract_views import get_source
from nti.app.base.abstract_views import AuthenticatedViewMixin
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfile import validate_sources
from nti.app.contentfile import get_content_files
from nti.app.contentfile import read_multipart_sources

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums.interfaces import IPost

from nti.externalization.interfaces import StandardExternalFields


def validate_attachments(user=None, context=None, sources=()):
    sources = sources or ()

    # check source contraints
    validate_sources(user, context, sources)

    # take ownership
    for source in sources:
        source.__parent__ = context


class PostUploadMixin(AuthenticatedViewMixin,
                      ModeledContentUploadRequestUtilsMixin):
    """
    Support for uploading of IPost objects.
    """

    def readInput(self, value=None):
        if not self.request.POST:
            externalValue = super(PostUploadMixin, self).readInput(value)
        else:
            externalValue = get_source(self.request, 'json')  # test legacy ipad
            if externalValue:
                value = externalValue.read()
                externalValue = super(PostUploadMixin, self).readInput(value)
            else:
                externalValue = super(PostUploadMixin, self).readInput(value)
        return externalValue

    def _read_incoming_post(self, datatype, constraint):
        # Note the similarity to ugd_edit_views
        creator = self.getRemoteUser()
        externalValue = self.readInput()

        if '/' in datatype:
            externalValue[StandardExternalFields.MIMETYPE] = datatype
        else:
            externalValue[StandardExternalFields.CLASS] = datatype

        containedObject = self.createAndCheckContentObject(creator, datatype,
                                                           externalValue, creator,
                                                           constraint)
        containedObject.creator = creator

        # The process of updating may need to index and create KeyReferences
        # so we need to have a jar. We don't have a parent to inherit from just yet
        # (If we try to set the wrong one, it messes with some events and some
        # KeyError detection in the containers)
        # containedObject.__parent__ = owner
        owner_jar = IConnection(self.request.context)
        if owner_jar and IConnection(containedObject, None) is None:
            owner_jar.add(containedObject)

        # Update the object, but don't fire any modified events. We don't know
        # if we'll keep this object yet, and we haven't fired a created event
        self.updateContentObject(containedObject, externalValue, set_id=False,
                                 notify=False)
        # Which just verified the validity of the title.

        sources = get_content_files(containedObject)
        if sources and self.request and self.request.POST:
            read_multipart_sources(self.request, sources.values())
        if sources:
            validate_attachments(self.remoteUser, 
                                 containedObject, 
                                 tuple(sources.values()))
        return containedObject, externalValue

    def _find_factory_from_precondition(self, forum):
        provided_by_forum = interface.providedBy(forum)
        forum_container_precondition = \
            provided_by_forum.get('__setitem__').getTaggedValue('precondition')

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

    def _get_topic_creator(self):
        return self.getRemoteUser()

    def _do_call(self):
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
        topic.description = external_value.get('description', topic.title)

        # For these, the name matters. We want it to be as pretty as we can get
        # TODO: We probably need to register an IReservedNames that forbids
        # _VIEW_CONTENTS and maybe some other stuff

        name = INameChooser(forum).chooseName(topic.title, topic)

        lifecycleevent.created(topic)
        forum[name] = topic  # Now store the topic and fire lifecycleevent.added
        assert topic.id == name
        assert topic.__parent__ == forum
        assert topic.containerId == forum.NTIID

        if headline_field:
            # not all containers have headlines; those that don't simply use
            # the incoming post as a template
            topic_post.__parent__ = topic  # must set __parent__ first for acquisition to work
            topic_post.creator = topic.creator

            # In order to meet the validity requirements, we must work from the root down,
            # only assigning the sublocation once the parent location is fully valid
            # (otherwise we get schema validation errors)...
            topic.headline = topic_post

            # ...this means, however, that the initial ObjectAddedEvent did not get fired
            # for the headline post (since it just now became a sublocation) so we must do
            # it manually
            lifecycleevent.created(topic_post)
            lifecycleevent.added(topic_post)

            # The actual name isn't tremendously important,
            # but we need to have one so that the lineage is set
            # correctly for when we're rendering links.
            topic_post.__name__ = topic.generateId(prefix='comment')

            # fail hard if no parent is set
            assert topic_post.__parent__ == topic

        # Respond with the pretty location of the object, within the blog
        self.request.response.status_int = 201  # created
        self.request.response.location = self.request.resource_path(topic)
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

    def _do_call(self):
        topic = self.request.context

        comment_factory_name, _, comment_iface = \
            self._find_factory_from_precondition(topic)

        incoming_post, _ = self._read_incoming_post(comment_factory_name,
                                                    comment_iface.providedBy)

        # The actual name of these isn't tremendously important
        name = topic.generateId(prefix='comment')

        lifecycleevent.created(incoming_post)
        # incoming_post.id and containerId are set automatically when it is added
        # to the container (but note that the created event did not have them)
        # Now store the topic and fire IObjectAddedEvent (subtype of
        # IObjectModifiedEvent)
        topic[name] = incoming_post

        # fail hard if no parent is set
        assert incoming_post.__parent__ == topic

        # Respond with the pretty location of the object
        self.request.response.status_int = 201  # created
        self.request.response.location = self.request.resource_path(
            incoming_post)
        return incoming_post


import six

from nti.base._compat import unicode_

from nti.contentprocessing.content_utils import tokenize_content
from nti.contentprocessing.content_utils import get_content_translation_table


def get_content(text=None, language='en'):
    result = ()
    text = unicode_(text) if text else None
    if text:
        table = get_content_translation_table(language)
        result = tokenize_content(text.translate(table), language)
    result = ' '.join(result)
    return unicode_(result)


class ContentResolver(object):

    def __init__(self, context, default=None):
        self.context = context

    @property
    def content(self):
        try:
            result = []
            for x in self.context.body:
                if isinstance(x, six.string_types):
                    result.append(get_content(x) or '')
            return ''.join(result)
        except AttributeError:
            return None
