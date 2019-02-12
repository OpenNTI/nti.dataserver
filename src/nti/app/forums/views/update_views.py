#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import interface

from nti.app.contentfile import transfer_internal_content_data

from nti.app.forums.views.view_mixins import validate_attachments

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver import authorization as nauth

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IDFLHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.interfaces import ICommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import ISendEmailOnForumTypeCreation

_view_defaults = dict(route_name='objects.generic.traversal', renderer='rest')


@view_config(context=IGeneralForum)
@view_defaults(permission=nauth.ACT_UPDATE,
               request_method='PUT',
               **_view_defaults)
class ForumObjectPutView(UGDPutView):
    """
    Editing an existing forum etc
    """

    def readInput(self):
        externalValue = super(ForumObjectPutView, self).readInput()
        # remove read only properties
        for name in ('TopicCount', 'NewestDescendantCreatedTime', 'NewestDescendant'):
            externalValue.pop(name, None)
        return externalValue


@view_config(context=IHeadlinePost)
@view_config(context=IPersonalBlogEntry)
@view_config(context=IPersonalBlogComment)
@view_config(context=IGeneralForumComment)
@view_config(context=IGeneralHeadlinePost)
@view_config(context=IPersonalBlogEntryPost)
@view_defaults(permission=nauth.ACT_UPDATE,
               request_method='PUT',
               **_view_defaults)
class PostObjectPutView(UGDPutView):
    """
    Editing an existing post, comments etc
    """

    def readInput(self):
        externalValue = super(PostObjectPutView, self).readInput()
        return externalValue

    def updateContentObject(self, contentObject, externalValue, set_id=False, notify=True):
        result = UGDPutView.updateContentObject(self,
                                                contentObject=contentObject,
                                                externalValue=externalValue,
                                                set_id=set_id,
                                                notify=notify)
        sources = transfer_internal_content_data(contentObject,
                                                 request=self.request,
                                                 ownership=False)
        if sources:
            validate_attachments(self.remoteUser, contentObject, sources)
        return result


@view_config(context=IDFLHeadlineTopic)
@view_config(context=IGeneralHeadlineTopic)
@view_config(context=ICommunityHeadlineTopic)  # Needed?
@view_defaults(permission=nauth.ACT_UPDATE,
               request_method='PUT',
               **_view_defaults)
class CommunityTopicPutDisabled(object):
    """
    Restricts PUT on topics to return 403. In pyramid 1.5 this otherwise
    would find the PUT for the superclass of the object, but we don't want to
    allow it. (In pyramid 1.4 it resulted in a 404)
    """

    def __init__(self, request):
        pass

    def __call__(self):
        raise hexc.HTTPForbidden('Connot PUT to a topic')


del _view_defaults
