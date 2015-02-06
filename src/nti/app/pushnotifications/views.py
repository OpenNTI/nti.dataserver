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

from nti.dataserver.authorization import ACT_READ

@view_config(route_name='objects.generic.traversal',
			 request_method='GET',
			 permission=ACT_READ,
			 name='unsubscribe_digest_email')
class UnsubscribeFromEmailSummaryPush(AbstractAuthenticatedView):
	"""
	A named view that, when fetched with GET, will change the
	preference of the authenticated user (NOT the user in the path, if there is one)
	to no longer receive automated emails. This corresponds to the
	``email_a_summary_of_interesting_changes`` preference in the
	:class:`.IEmailPushNotificationSettings` class. While this view
	will work with any context, since it implicitly acts on the current user,
	it's best for logging purposes to generate links that include the user
	in the path.

	We may register this view as a ``token`` based view so that
	authentication is automatic, but it is safer to require explicit
	authentication (in my experience it seems to be about 50/50 for
	what sites do, and in general the more likely the email is
	valuable to you and not marketing spam the more likely they are to
	require authentication); we'll go with that to start with and see
	if we get complaints.
	"""

	def __call__(self):
		request = self.request
		environ = request.environ
		if not environ.get('REMOTE_USER') or not environ.get('repoze.who.identity'): # pragma: no cover
			# Hmm, entirely unauthenticated. Did we have an entirely
			# public resource?
			return request.response

		# Make a sub-request to set the preference, thus coupling us
		# only to the path, not the implementation. (Is this better or
		# worse than accessing the named utility?)

		path = '/dataserver2/users/' + environ['REMOTE_USER'] + '/++preferences++/PushNotifications/Email'
		data = {'email_a_summary_of_interesting_changes': False}
		json = simplejson.dumps(data)

		subrequest = request.blank(path)
		subrequest.method = b'PUT'
		subrequest.environ[b'REMOTE_USER'] = environ['REMOTE_USER']
		subrequest.environ[b'repoze.who.identity'] = environ['repoze.who.identity'].copy()
		subrequest.body = json # NOTE: this will be a pain point under py3, body vs text
		# Make sure we look like a programatic request
		subrequest.environ[b'HTTP_X_REQUESTED_WITH'] = b'xmlhttprequest'
		subrequest.possible_site_names = request.possible_site_names
		self.request.invoke_subrequest( subrequest )

		request.environ['nti.request_had_transaction_side_effects'] = True # must commit the change

		# We should probably redirect to a prettier URL?
		request.response.text = _('Thank you. You have been unsubscribed.') # This is not actually translated
		return request.response
