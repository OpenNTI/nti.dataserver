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

from itsdangerous import BadSignature

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from zope import component
from zope.security.interfaces import IParticipation
from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import restoreInteraction
from zope.preference.interfaces import IPreferenceGroup

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.pushnotifications.utils import validate_signature

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.users.users import User

def _do_unsubscribe( request, user ):
	prefs = component.getUtility(IPreferenceGroup, name='PushNotifications.Email')
	endInteraction()
	try:
		newInteraction( IParticipation( user ) )
		prefs.email_a_summary_of_interesting_changes = False
	finally:
		restoreInteraction()

	request.environ['nti.request_had_transaction_side_effects'] = True # must commit the change

	# TODO We should probably redirect to a prettier URL?
	request.response.text = _('Thank you. You have been unsubscribed.') # This is not actually translated
	return request.response

@view_config(route_name='objects.generic.traversal',
			 request_method='GET',
			 context=IDataserverFolder,
			 name='unsubscribe_digest_email_with_token')
class UnsubscribeWithTokenFromEmailSummaryPush( object ):
	"""
	Our unathenticated token view to unsubscribe from email
	verification.  See ``UnsubscribeFromEmailSummaryPush``.
	"""

	def __init__(self, request):
		self.request = request

	def __call__(self):
		request = self.request
		values = CaseInsensitiveDict(**request.params)
		signature = values.get('signature')

		username = values.get('username')
		if not username:
			raise hexc.HTTPUnprocessableEntity(_("No username specified."))
		user = User.get_user(username)
		# TODO Danger of too much info, fishing?
		# Maybe we need a generic invalid signature message.
		if user is None:
			raise hexc.HTTPUnprocessableEntity(_("User not found."))

		try:
			validate_signature(user, signature)
		except BadSignature:
			raise hexc.HTTPUnprocessableEntity(_("Invalid signature."))
		except ValueError as e:
			msg = _(str(e))
			raise hexc.HTTPUnprocessableEntity(msg)

		result = _do_unsubscribe( request, user=user )
		return result

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
		username = environ['REMOTE_USER']
		user = User.get_user( username )
		result = _do_unsubscribe( request, user )
		return result
