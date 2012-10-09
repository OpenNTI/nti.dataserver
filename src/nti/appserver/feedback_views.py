#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to sending feedback.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from pyramid import interfaces as pyramid_interfaces

from pyramid.view import view_config

from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth

from ._util import link_belongs_to_user

#: The link relationship type to which an authenticated
#: user can POST data to send feedback. Also the name of a
#: view to handle this feedback: :func:`send_feedback_view`
REL_SEND_FEEDBACK = 'send-feedback'

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IUser,
			  permission=nauth.ACT_READ,
			  request_method='POST',
			  name=REL_SEND_FEEDBACK )
def send_feedback_view( request ):
	logger.warning("Feedback view unimplemented")
	return True

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser,pyramid_interfaces.IRequest)
class FeedbackLinkProvider(object):

	def __init__( self, user=None, request=None ):
		self.user = user

	def get_links( self ):
		link = Link( self.user,
					 rel=REL_SEND_FEEDBACK,
					 elements=( '@@' + REL_SEND_FEEDBACK, ) )
		link_belongs_to_user( link, self.user )
		return (link,)
