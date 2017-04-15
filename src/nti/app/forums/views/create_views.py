#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.forums import VIEW_CONTENTS

from nti.app.forums.views.view_mixins import AbstractBoardPostView
from nti.app.forums.views.view_mixins import _AbstractForumPostView
from nti.app.forums.views.view_mixins import _AbstractTopicPostView

from nti.dataserver import authorization as nauth

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

_view_defaults = dict(route_name='objects.generic.traversal',
                      renderer='rest')
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update(permission=nauth.ACT_CREATE,
                        request_method='POST')
_r_view_defaults = _view_defaults.copy()
_r_view_defaults.update(permission=nauth.ACT_READ,
                        request_method='GET')
_d_view_defaults = _view_defaults.copy()
_d_view_defaults.update(permission=nauth.ACT_DELETE,
                        request_method='DELETE')

# We allow POSTing comments/topics/forums to the actual objects, and also
# to the /contents sub-URL (ignoring anything subpath after it)
# This lets a HTTP client do a better job of caching, by
# auto-invalidating after its own comment creation
# (Of course this has the side-problem of not invalidating
# a cache of the topic object itself...)


@view_config(name='')
@view_config(name=VIEW_CONTENTS)
@view_defaults(context=frm_interfaces.IBoard,
               **_c_view_defaults)
class BoardPostView(AbstractBoardPostView):
    """
    Given an incoming post, create a new forum.
    """


@view_config(name='')
@view_config(name=VIEW_CONTENTS)
@view_defaults(context=frm_interfaces.ICommunityBoard,
               **_c_view_defaults)
class CommunityBoardPostView(AbstractBoardPostView):

    # XXX: We can do better
    def _get_topic_creator(self):
        return self.request.context.creator  # the community


@view_config(name='')
@view_config(name=VIEW_CONTENTS)
@view_defaults(context=frm_interfaces.IDFLBoard,
               **_c_view_defaults)
class DFLBoardPostView(AbstractBoardPostView):

    # XXX: We can do better
    def _get_topic_creator(self):
        return self.request.context.creator  # the dfl


@view_config(name='')
@view_config(name=VIEW_CONTENTS)
@view_defaults(context=frm_interfaces.IForum,
               **_c_view_defaults)
class ForumPostView(_AbstractForumPostView):
    """
    Given an incoming post, create a new topic.
    """


@view_config(name='')
@view_config(name=VIEW_CONTENTS)
@view_defaults(context=frm_interfaces.ITopic,
               **_c_view_defaults)
class TopicPostView(_AbstractTopicPostView):
    """
    Given an incoming post, create a new comment.
    """


del _view_defaults
del _c_view_defaults
del _r_view_defaults
del _d_view_defaults
