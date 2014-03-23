#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyramid views related to push notifications.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import simplejson

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver.interfaces import IUser

@view_config(route_name='objects.generic.traversal',
			 request_method='GET',
			 context=IUser,
			 name='unsubscribe')
class UnsubscribeFromEmailSummaryPush(AbstractAuthenticatedView):
	"""
	A named view that, when fetched with GET, will change the
	preference of the authenticated user (NOT the user in the path)
	to no longer receive automated emails. This corresponds to the
	``email_a_summary_of_interesting_changes`` preference in the
	:class:`.IEmailPushNotificationSettings` class.

	We typically expect this view to be registered as a ``token`` based
	view so that authentication is automatic.
	"""

	def __call__(self):
		# Make a sub-request to set the preference, thus coupling us
		# only to the path, not the implementation
		request = self.request

		path = '/dataserver2/users/' + self.context.username + '/++preferences++/PushNotifications/Email'
		data = {'email_a_summary_of_interesting_changes': False}
		json = simplejson.dumps(data)

		subrequest = request.blank(path)
		subrequest.method = b'PUT'
		subrequest.environ[b'REMOTE_USER'] = request.environ['REMOTE_USER']
		subrequest.environ[b'repoze.who.identity'] = request.environ['repoze.who.identity'].copy()
		subrequest.body = json # NOTE: this will be a pain point under py3, body vs text
		# Make sure we look like a programatic request
		subrequest.environ[b'HTTP_X_REQUESTED_WITH'] = b'xmlhttprequest'

		self.request.invoke_subrequest( subrequest )

		request.environ['nti.request_had_transaction_side_effects'] = True # must commit the change

		# We should probably redirect to a prettier URL?
		request.response.text = _('Thank you. You have been unsubscribed.') # This is not actually translated
		return request.response
