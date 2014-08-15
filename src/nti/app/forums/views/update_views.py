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
from pyramid.view import view_defaults  # NOTE: Only usable on classes
from pyramid import httpexceptions as hexc

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver import authorization as nauth


# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

_view_defaults = dict(  route_name='objects.generic.traversal',
						renderer='rest' )

@view_config(context=frm_interfaces.IHeadlinePost)
@view_config(context=frm_interfaces.IPersonalBlogEntry)
@view_config(context=frm_interfaces.IPersonalBlogEntryPost)
@view_config(context=frm_interfaces.IPersonalBlogComment)
@view_config(context=frm_interfaces.IGeneralForumComment)
@view_config(context=frm_interfaces.IGeneralHeadlinePost)
@view_config(context=frm_interfaces.IGeneralForum)
@view_defaults( permission=nauth.ACT_UPDATE,
				request_method='PUT',
				**_view_defaults)
class ForumObjectPutView(UGDPutView):
	""" Editing an existing forum post, etc """

	def readInput(self):
		externalValue = super(ForumObjectPutView, self).readInput()
		theObject = self._get_object_to_update()
		if frm_interfaces.IForum.providedBy(theObject):
			# remove read only properties
			for name in ('TopicCount', 'NewestDescendantCreatedTime', 'NewestDescendant'):
				if name in externalValue:
					del externalValue[name]
		return externalValue

@view_config(context=frm_interfaces.ICommunityHeadlineTopic) # Needed?
@view_config(context=frm_interfaces.IGeneralHeadlineTopic)
@view_defaults( permission=nauth.ACT_UPDATE,
				request_method='PUT',
				**_view_defaults)
class CommunityTopicPutDisabled(object):
	"""Restricts PUT on topics to return 403. In pyramid 1.5 this otherwise
	would find the PUT for the superclass of the object, but we don't want to
	allow it. (In pyramid 1.4 it resulted in a 404)"""

	def __init__(self, request):
		pass

	def __call__(self):
		raise hexc.HTTPForbidden('Connot PUT to a topic')
