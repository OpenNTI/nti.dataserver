#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Listeners that take action for a user's stream, typically emitting notifications.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.event import notify

from zope.publisher.interfaces.browser import IBrowserRequest

from ZODB import loglevels

from z3c.table import table

from pyramid.threadlocal import get_current_request

from nti.appserver.policies.site_policies import get_possible_site_names

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import SC_CREATED
from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import DataChangedUserNotificationEvent

from nti.dataserver.users.interfaces import IUserProfile

from ._email_utils import queue_simple_html_text_email
from .interfaces import IChangePresentationDetails

@component.adapter(IUser, IStreamChangeEvent)
def user_change_broadcaster(user, change):
	"""
	Notifies the chat server of data change events so they can be
	put on the user's socket.
	"""
	if change.send_change_notice:
		logger.log(	loglevels.TRACE, 'Broadcasting incoming change to %s chg: %s',
					user.username, change.type)
		notify(DataChangedUserNotificationEvent((user.username,), change))

class ITemporaryChangeEmailMarker(interface.Interface):
	"Temporary marker interface, assigned using configuration to a user who wants to get change emails."

@interface.implementer(ITemporaryChangeEmailMarker)
class TemporaryChangeEmailMarker(object):
	pass

class NewNoteBodyTable(table.SequenceTable):
	pass

@component.adapter(IUser, IStreamChangeEvent)
def user_change_new_note_emailer(user, change):
	"""
	For incoming shared objects that are notes being freshly created,
	attempts to email them
	"""

	if change.type != SC_CREATED:
		return

	change_object = change.object
	# TODO: There is not one unifying interface
	# above objects that we want to send notices about
	# (IModeledContent works for notes and posts, but not
	# topics themselves).
	# if not nti_interfaces.IModeledContent.providedBy( change_object ):
	# 	return
	# So we drive this off whether we can get a
	# presentation
	change_presentation_details = component.queryMultiAdapter((change_object, change),
															   IChangePresentationDetails)
	if change_presentation_details is None:
		return

	profile = IUserProfile(user)
	email = getattr(profile, 'email', None)
	opt_in = getattr(profile, 'opt_in_email_communication', True)

	if not email or not opt_in:
		logger.log(	loglevels.TRACE,
					"User %s has no email (%s) or hasn't opted in (%s), no way to send notices",
					user, email, opt_in)
		return

	# Ok, now here's the tricky part. Until we have preferences or something about who/how to send
	# email, we're doing something a bit weird. We still want to be able to configure this, possibly
	# in site.zcml. We think we only want to do this for a very small handful of users. So the easy
	# thing to do is look up a named utility. We will use the username. We could also
	# use the groups the user belongs to in the same way acls do, or we could even look for
	# sites
	# TODO: Convert this to z3c.baseregistry?
	request = get_current_request()
	names = [user.username] + list(get_possible_site_names(request=request, include_default=True))
	send = False
	for name in names:
		if component.queryUtility(ITemporaryChangeEmailMarker, name=name):
			send = True
			logger.debug("Sending change email to %s due to configuration at %r", user, name)
			break
	if send:
		base_template = 'note_created_email'

		the_table = NewNoteBodyTable([change_object],
									  IBrowserRequest(request) if request else None)

		the_table.update()

		note_text = [component.queryAdapter(x, IPlainTextContentFragment, name='text', default='')
					 for x in change_object.body]

		queue_simple_html_text_email(
			base_template,
			subject=change_presentation_details.title,
			recipients=[user],
			template_args={'note': change_object,
						   'change': change,
						   'user': user,
						   'note_table': the_table,
						   'note_text': '\n'.join(note_text),
						   'profile': profile},
			request=request)
