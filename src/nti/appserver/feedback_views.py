#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to sending feedback.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import textwrap

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from pyramid import interfaces as pyramid_interfaces

from pyramid.view import view_config
from pyramid import security as psec

from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth

from . import httpexceptions as hexc
from ._util import link_belongs_to_user
from . import _email_utils
from ._external_object_io import read_body_as_external_object

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

	json_body = read_body_as_external_object( request )
	if 'body' not in json_body or not json_body['body'] or not unicode(json_body['body']).strip():
		raise hexc.HTTPBadRequest()

	request_details = dict(json_body)
	del request_details['body']
	request_details.update( request.environ )

	request_details_table = '\n\n    '.join( [k + '\t\t:' + repr(v) for k, v in sorted(request_details.items())] )


	_email_utils.queue_simple_html_text_email( 'platform_feedback_email',
											   subject="Feedback from %s" % psec.authenticated_userid(request),
											   recipients=['feedback@nextthought.com'],
											   template_args={'userid': psec.authenticated_userid(request),
															  'data': json_body,
															  'filled_body': '\n    '.join( textwrap.wrap( json_body['body'], 60 ) ),
															  'context': json_body,
															  'request': request,
															  'request_details': request_details,
															  'request_details_table': request_details_table},
											   request=request )

	return hexc.HTTPNoContent()
