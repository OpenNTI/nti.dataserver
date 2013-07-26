#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to forum administration.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface

import pyramid.httpexceptions  as hexc

from pyramid.view import view_config

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.appserver.utils import _JsonBodyView

@view_config(route_name='objects.generic.traversal',
			 name='set_class_community_forum',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class SetClassCommunityForum(_JsonBodyView):
	
	def __call__(self):
		values = self.readInput()
		community = values.get('community', '')
		community = users.Community.get_community(community)
		if not community or not nti_interfaces.ICommunity.providedBy(community):
			raise hexc.HTTPNotFound(detail='Community not found')
		
		instructors = values.get('instructors', ())
		if instructors and isinstance(instructors, six.string_types):
			instructors = instructors.split(',')
		if not instructors:
			raise hexc.HTTPUnprocessableEntity(detail='Sharing not specified')

		forum = frm_interfaces.ICommunityForum(community, None)
		if forum is None:
			raise hexc.HTTPUnprocessableEntity(detail='Community does not allow a forum')

		interface.alsoProvides(forum, frm_interfaces.IClassForum)
		setattr(forum, 'Instructors', list(set(instructors)))
		return hexc.HTTPNoContent()
