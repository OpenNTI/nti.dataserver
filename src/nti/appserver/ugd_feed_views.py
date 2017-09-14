#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for creating Atom and RSS feeds from UGD streams. Atom is highly recommended.

A typical URL will look something like ``/dataserver2/users/$USER/Pages($NTIID)/RecursiveStream/feed.atom.``
Your newsreader will need to support HTTP Basic Auth; on the Mac I highly
recommend NetNewsWire.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import datetime
from collections import namedtuple

import feedgenerator

from zope import component
from zope import interface

from zope.contentprovider.interfaces import IContentProvider
from zope.contentprovider.provider import ContentProviderBase

from zope.dublincore.interfaces import IDCTimes

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.appserver import httpexceptions as hexc

from nti.appserver.interfaces import IChangePresentationDetails

from nti.appserver.ugd_query_views import _RecursiveUGDStreamView

from nti.base._compat import unicode_

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ISelectedRange
from nti.dataserver.interfaces import IStreamChangeEvent

from nti.dataserver.users.interfaces import IUserProfile

from nti.ntiids.oids import to_external_ntiid_oid


class _BetterDateAtom1Feed(feedgenerator.Atom1Feed):
    """
    Provides the ``published`` element for atom feeds; if this
    is missing and only ``updated`` is present (the default in the super class)
    some readers will fail to present a valid date.
    """

    def add_item_elements(self, handler, item):
        super(_BetterDateAtom1Feed, self).add_item_elements(handler, item)
        if item.get('published') is not None:
            handler.addQuickElement(u"published",
                                    feedgenerator.rfc3339_date(item['published']).decode('utf-8'))


EntryDetails = namedtuple('EntryDetails',
                          ['object', 'creator', 'title', 'categories'])


class AbstractFeedView(object):
    """
    Primary view for producing Atom and RSS feeds.

    Accepts the same filtering parameters as
    :class:`nti.appserver.ugd_query_views._RecursiveUGDStreamView` so
    you can control what types of actions you see in the feed as well
    as the length of the feed.

    """

    def __init__(self, request):
        self.request = request

    # TODO: We could probably do this with named adapters
    _data_callable_factory = None

    def _object_and_creator(self, data_item):
        """
        Returns an :class:`EntryDetails`, which is a named four tuple:
        (object, creator, title, categories).

        The ``object`` is the data object for the feed entry item.
        An adapter between it, the request, and this view will
        be queried to get an :class:`.IContentProvider` to render the body
        of the item.

        The ``creator`` is the user object that created the data object, or
        is otherwise responsible for its appearance.

        The ``title`` is the string giving the title of the entry.

        The ``categories`` is a list of strings giving the categories of the
        entry. Many RSS readers will present these specially; they might also be added
        to the rendered body.

        When the change is an :class:`.IStreamChangeEvent`, this will be a
        :class:`.IChangePresentationDetails`.

        """
        raise NotImplementedError()

    def _feed_title(self):
        raise NotImplementedError()

    def __call__(self):
        request = self.request
        response = request.response

        stream_view = self._data_callable_factory(request)
        ext_dict = stream_view()  # May raise HTTPNotFound
        response.last_modified = ext_dict['Last Modified']

        # TODO: This borrows alot from the REST renderers
        if response.last_modified is not None and request.if_modified_since:
            # Since we know a modification date, respect If-Modified-Since. The spec
            # says to only do this on a 200 response
            # This is a pretty poor time to do it, after we've done all this
            # work
            if response.last_modified <= request.if_modified_since:
                not_mod = hexc.HTTPNotModified()
                not_mod.last_modified = response.last_modified
                not_mod.cache_control = 'must-revalidate'
                raise not_mod

        if request.view_name == 'feed.rss':
            feed_factory = feedgenerator.Rss201rev2Feed 
        else:
            feed_factory = _BetterDateAtom1Feed

        feed = feed_factory(title=self._feed_title(),
                            link=request.application_url,
                            feed_url=request.path_url,
                            description='',
                            language='en')

        for data_item in ext_dict['Items']:
            data_object, data_creator, data_title, data_categories = \
                                        self._object_and_creator(data_item)

            descr = ''
            renderer = component.queryMultiAdapter((data_object, request, self), 
                                                   IContentProvider)
            if renderer:
                renderer.update()
                descr = renderer.render()

            creator_profile = IUserProfile(data_creator)
            data_oid = to_external_ntiid_oid(data_object)
            feed.add_item(
                title=data_title,
                # Direct link to the object, using a fragment and
                # assuming the app can interpret what that means.
                # Better would be something that involved the server
                link=request.application_url + '#!' + data_oid,
                description=descr,
                author_email=getattr(creator_profile, 'email', None),
                author_name=data_creator,
                pubdate=IDCTimes(data_item).created,
                unique_id=data_oid,
                categories=data_categories,
                # extras. If we don't provide a 'published' date
                updated=IDCTimes(data_item).modified,
                published=IDCTimes(data_item).created,
            )

        feed_string = feed.writeString('utf-8')
        response.content_type = feed.mime_type.encode('utf-8')
        response.body = feed_string
        return response


@interface.implementer(IChangePresentationDetails)
@component.adapter(interface.Interface, IStreamChangeEvent)
def ChangePresentationDetails(_, change):
    # NOTE: This has too much logic and knows about
    # too many types; this could be split out
    # using the new adapter mechanism.
    # Consequently, our registration is wrong.

    # TODO: Where should this be defined? Is it localizable strings?
    # We could even customize titles by using adapters
    _pretty_type_names = {'Note': 'note',
                          'PersonalBlogEntry': 'blog entry',
                          'CommunityHeadlineTopic': 'discussion',
                          'GeneralForumComment': 'discussion comment'}

    creator_profile = IUserProfile(change.creator)

    prettyname_creator = creator_profile.realname \
                      or creator_profile.alias \
                      or unicode_(change.creator)
    prettyname_action_kind = change.type.lower()
    # if it's proxied, type() would be wrong
    prettyname_object_kind = change.object.__class__.__name__
    prettyname_object_kind = _pretty_type_names.get(prettyname_object_kind,
                                                    prettyname_object_kind)

    title = "%s %s a %s" % (prettyname_creator,
                            prettyname_action_kind,
                            prettyname_object_kind)

    if getattr(change.object, 'title', None):
        title = '%s: "%s"' % (title, change.object.title)

    return EntryDetails(change.object, change.creator, title, (change.type,))


@view_config(context='nti.appserver.interfaces.IPageContainerResource',
             name='feed.rss')
@view_config(context='nti.appserver.interfaces.IPageContainerResource',
             name='feed.atom')
@view_config(context='nti.appserver.interfaces.IRootPageContainerResource',
             name='feed.atom')
@view_config(context='nti.appserver.interfaces.IRootPageContainerResource',
             name='feed.rss')
@view_defaults(route_name='objects.generic.traversal',
               permission=nauth.ACT_READ, request_method='GET',
               http_cache=datetime.timedelta(hours=1))
class UGDFeedView(AbstractFeedView):

    _data_callable_factory = _RecursiveUGDStreamView

    def _object_and_creator(self, change):
        return component.getMultiAdapter((change.object, change),
										 IChangePresentationDetails)

    def _feed_title(self):
        return self.request.context.ntiid  # TODO: Better title


# TODO: Not sure these belong here, or where they belong
from nti.appserver._table_utils import NoteContentProvider


@interface.implementer(IContentProvider)
@component.adapter(INote, interface.Interface, AbstractFeedView)
class NoteFeedRenderer(NoteContentProvider):
    """
    Renderers notes in HTML for feeds. Does what it can with canvas objects,
    which is to include their URL.
    """


@interface.implementer(IContentProvider)
@component.adapter(ISelectedRange, interface.Interface, AbstractFeedView)
class SelectedRangeFeedRenderer(ContentProviderBase):
    """
    For highlights and the like.
    """

    def render(self):
        return self.context.selectedText


@interface.implementer(IContentProvider)
@component.adapter(IEntity, interface.Interface, AbstractFeedView)
class EntityFeedRenderer(ContentProviderBase):
    """
    For circled users.
    """

    def render(self):
        return self.context.username
