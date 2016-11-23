#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import component

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.common._compat import aq_base

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic

import zope.deferredimport
zope.deferredimport.defineFrom(
	"nti.app.forums.views.view_mixins",
	"AbstractBoardPostView",
	"_AbstractForumPostView",
	"_AbstractTopicPostView")

zope.deferredimport.defineFrom(
	"nti.app.forums.views.create_views",
	"_c_view_defaults")

@component.adapter(IPost, IObjectModifiedEvent)
def match_title_of_post_to_blog( post, event ):
	"""
	When the main story of a story topic (blog post) is modified, match the titles
	"""

	if 		IHeadlineTopic.providedBy( post.__parent__ ) \
		and aq_base(post) is aq_base(post.__parent__.headline) \
		and post.title != post.__parent__.title:
		post.__parent__.title = post.title
	return
