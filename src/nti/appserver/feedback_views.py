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

from pyramid.view import view_config
from pyramid import security as psec

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from . import _email_utils
from . import httpexceptions as hexc
from ._external_object_io import read_body_as_external_object

#: The link relationship type to which an authenticated
#: user can POST data to send feedback. Also the name of a
#: view to handle this feedback: :func:`send_feedback_view`
REL_SEND_FEEDBACK = 'send-feedback'

def _format_email( request, body_key, userid, report_type, subject, to ):

	json_body = read_body_as_external_object( request )
	if body_key not in json_body or not json_body[body_key] or not unicode(json_body[body_key]).strip():
		raise hexc.HTTPBadRequest()

	request_info = dict(json_body)
	# No need to repeat it here
	del request_info[body_key]

	def _format_table(tbl):
		if not tbl:
			return ''
		key_width = len(max(tbl, key=len))

		lines = [(str(k).ljust( key_width + 10 ) + repr(v))
				 for k, v
				 in sorted(tbl.items())]
		return '\n\n    '.join( lines )

	request_info_table = _format_table( request_info )
	request_detail_table = _format_table( request.environ )

	# The template expects 'body' so ensure that's what it gets
	json_body['body'] = json_body[body_key]

	_email_utils.queue_simple_html_text_email( 'platform_feedback_email',
											   subject=subject % userid,
											   recipients=[to],
											   template_args={'userid': userid,
															  'report_type': report_type,
															  'data': json_body,
															  'filled_body': '\n    '.join( textwrap.wrap( json_body[body_key], 60 ) ),
															  'context': json_body,
															  'request': request,
															  'request_info': request_info,
															  'request_info_table': request_info_table,
															  'request_details_table': request_detail_table },
											   request=request )

	return hexc.HTTPNoContent()

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IUser,
			  permission=nauth.ACT_READ,
			  request_method='POST',
			  name=REL_SEND_FEEDBACK )
def send_feedback_view( request ):

	return _format_email( request,
						  'body',
						  psec.authenticated_userid(request),
						  'Feedback',
						  'Feedback From %s',
						  'feedback@nextthought.com' )


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IDataserverFolder,
			  request_method='POST',
			  name="send-crash-report" )
def send_crash_report_view( request ):
	"""
	This is a view that requires no authentication (which may open it to abuse)
	and takes a small set of data the app sends it as a JSON dictionary containing
	the ``message``, ``file`` and ``line`` entries and sends a support
	email. To help prevent abuse, ``message`` is capped in size.
	"""
	# Not actually enforcing any of that now.

	userid = psec.authenticated_userid(request) or psec.unauthenticated_userid(request) or "unknown"

	return _format_email( request,
						  'message',
						  userid,
						  'Crash Report',
						  'Crash Report From %s',
						  'support@nextthought.com' )
