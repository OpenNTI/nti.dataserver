#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters for forum objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.publisher.browser import BrowserView

from zc.displayname.adapters import convertName
from zc.displayname.interfaces import IDisplayNameGenerator

from pyramid.interfaces import IRequest

from nti.app.forums import MessageFactory as _

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog

from nti.namedfile.constraints import FileConstraints

logger = __import__('logging').getLogger(__name__)


@interface.implementer_only(IDisplayNameGenerator)
@component.adapter(IPersonalBlog, IRequest)
class _PersonalBlogDisplayNameGenerator(BrowserView):
    """
    Give's a better display name to the user's blog, which
    would ordinarily just get their user name.
    """

    def __call__(self):
        user = self.context.__parent__
        user_display_name = component.getMultiAdapter((user, self.request),
                                                      IDisplayNameGenerator)
        user_display_name = user_display_name()

        result = _(u"${username}'s Thoughts",
                   mapping={'username': user_display_name})

        result = convertName(result, self.request, None)
        return result


class _PostFileConstraints(FileConstraints):
    max_file_size = 10485760  # 10 MB

    max_files = 10

    max_total_file_size = 26214400 # 25 MB
