#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters for forum objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import component
from zope import interface

from zope.publisher.browser import BrowserView

from zc.displayname.adapters import convertName
from zc.displayname.interfaces import IDisplayNameGenerator

from pyramid.interfaces import IRequest

from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog

from nti.namedfile.file import FileConstraints

from .interfaces import ITopicFileConstraints

@interface.implementer_only(IDisplayNameGenerator)
@component.adapter(IPersonalBlog, IRequest)
class _PersonalBlogDisplayNameGenerator(BrowserView):
	"""
	Give's a better display name to the user's blog, which
	would ordinarily just get their user name.
	"""

	def __call__(self):
		user = self.context.__parent__
		user_display_name = component.getMultiAdapter( (user, self.request),
													   IDisplayNameGenerator)
		user_display_name = user_display_name()

		result = _("${username}'s Thoughts",
				   mapping={'username': user_display_name} )

		result = convertName(result, self.request, None)
		return result

@component.adapter(ITopic)
@interface.implementer(ITopicFileConstraints)
class _TopicFileConstraints(FileConstraints):
	max_files = 1
	max_file_size = 20000000 # 20 MB
