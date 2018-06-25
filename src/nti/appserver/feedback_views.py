#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to sending feedback.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import textwrap
from pprint import pprint
from cgi import escape as html_escape

from zope import component

from pyramid.view import view_config

from nti.app.externalization.internalization import read_body_as_external_object

from nti.appserver import httpexceptions as hexc

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.mailer.interfaces import ITemplatedMailer


#: The link relationship type to which an authenticated
#: user can POST data to send feedback. Also the name of a
#: view to handle this feedback: :func:`send_feedback_view`
REL_SEND_FEEDBACK = 'send-feedback'


def _format_email(request, body_key, userid, report_type, subject, to, include_request_details=True):
    json_body = read_body_as_external_object(request)
    if     body_key not in json_body \
        or not json_body[body_key] \
        or not unicode(json_body[body_key]).strip():
        raise hexc.HTTPBadRequest()

    request_info = dict(json_body)
    # No need to repeat it here
    del request_info[body_key]

    def _enc(v):
        if isinstance(v, six.text_type):
            v = v.encode('utf-8', errors='ignore')
        return v

    def _dec(v):
        if not isinstance(v, six.text_type):
            v = v.decode('utf-8', errors='ignore')
        return v

    def _formatted(v, as_html=False, text_pfx=''):
        """
        Returns a text string (unicode under py2)
        """
        if not isinstance(v, basestring):
            if isinstance(v, dict):
                v = sorted([(_enc(kk), _enc(vv)) for kk, vv in v.items()])
            if isinstance(v, list):
                v = [_enc(vv) for vv in v]
            buf = six.StringIO()
            pprint(v, stream=buf, width=50)
            v = buf.getvalue()
        v = _enc(v)

        if as_html:
            v = html_escape(v)
            v = _dec(v)
            v = v.replace('\n', '<br />')
        else:
            v = _dec(v)
            v = v.replace('\n', '\n' + text_pfx)

        return v

    def _format_table(tbl):
        """Returns a text string (unicode under py2)"""
        if not tbl:
            return ''
        # Make everything line up nicely, even with multiple lines in a value
        key_width = len(max(tbl, key=len))
        val_line_pfx = ' ' * (key_width + 10)
        lines = [
            (six.text_type(k).ljust(key_width + 10) + _formatted(v, text_pfx=val_line_pfx))
            for k, v in sorted(tbl.items())
        ]
        return '\n\n    '.join(lines)

    request_info_table = _format_table(request_info)
    # Some things we want to take out of the environment,
    # notably cookies, which may contain sensitive information;
    # in particular, our nti.auth_tkt cookie is NOT using
    # IP address, so it could be used by anyone until it times out.
    if include_request_details:
        request_details = dict(request.environ)
    else:
        request_details = {}
    
    # TODO: Preserve just the names? Blacklist only certain cookies?
    for k in ('HTTP_COOKIE',
              'paste.cookies',
              'webob._parsed_cookies',
              'HTTP_AUTHORIZATION',
              'repoze.who.api',
              'repoze.who.identity'):
        request_details.pop(k, None)

    request_detail_table = _format_table(request_details)

    # The template expects 'body' so ensure that's what it gets
    json_body['body'] = json_body[body_key]

    # Pre sort and name the tables so the template doesn't have to. Also do some
    # pretty printing for the incoming info items
    def _format_html_items(items):
        request_info_items = []
        for k, v in items or ():
            request_info_items.append((k, _formatted(v, True)))
        return sorted(request_info_items)

    tables = [
        {'name': 'Request Information', 'data': _format_html_items(request_info.items())},
        {'name': 'Request Details',     'data': _format_html_items(request_details.items())}
    ]

    environ_dict = request_details or dict(request.environ)
    cur_domain = environ_dict.get(
        'HTTP_HOST', environ_dict.get('SERVER_NAME'))
    cur_domain = cur_domain.split(':')[0]  # drop port
    mailer = component.getUtility(ITemplatedMailer)
    mailer.queue_simple_html_text_email(
        'platform_feedback_email',
        subject=subject % (userid, cur_domain),
        recipients=[to],
        template_args={'userid': userid,
                       'report_type': report_type,
                       'data': json_body,
                       'filled_body': '\n    '.join(textwrap.wrap(json_body[body_key], 60)),
                       'context': json_body,
                       'request': request,
                       'tables': tables,
                       'request_info_table': request_info_table or None,
                       'request_details_table': request_detail_table or None},
        text_template_extension='.mak',
        request=request)

    return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=nti_interfaces.IUser,
             permission=nauth.ACT_READ,
             request_method='POST',
             name=REL_SEND_FEEDBACK)
def send_feedback_view(request):

    return _format_email(request,
                         'body',
                         request.authenticated_userid,
                         'Feedback',
                         'Feedback From %s on %s',
                         'support@nextthought.com',
                         include_request_details=False)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=nti_interfaces.IDataserverFolder,
             request_method='POST',
             name="send-crash-report")
def send_crash_report_view(request):
    """
    This is a view that requires no authentication (which may open it to abuse)
    and takes a small set of data the app sends it as a JSON dictionary containing
    the ``message``, ``file`` and ``line`` entries and sends a support
    email. To help prevent abuse, ``message`` is capped in size.
    """
    # Not actually enforcing any of that now.
    userid = request.authenticated_userid or request.unauthenticated_userid or "unknown"
    return _format_email(request,
                         'message',
                         userid,
                         'Crash Report',
                         'Crash Report From %s on %s',
                         'crash.reports@nextthought.com')
