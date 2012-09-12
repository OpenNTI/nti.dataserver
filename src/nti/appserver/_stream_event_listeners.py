#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Listeners that take action for a user's stream, typically emitting notifications.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.threadlocal import get_current_request

from nti.appserver._email_utils import queue_simple_html_text_email
from nti.appserver import site_policies

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.contentfragments import interfaces as frg_interfaces

from zope.event import notify
from zope import component
from zope import interface

from z3c.table import table
from nti.appserver.z3c_zpt import PyramidZopeRequestProxy


@component.adapter( nti_interfaces.IUser, nti_interfaces.IStreamChangeEvent )
def user_change_broadcaster( user, change ):
	"""
	Notifies the chat server of data change events so they can be
	put on the user's socket.
	"""
	logger.debug( 'Broadcasting incoming change to %s chg: %s', user.username, change.type)
	notify( chat_interfaces.DataChangedUserNotificationEvent( (user.username,), change ) )


class ITemporaryChangeEmailMarker(interface.Interface):
	"Temporary marker interface, assigned during configuration to a user who wants to get change emails."

@interface.implementer(ITemporaryChangeEmailMarker)
class TemporaryChangeEmailMarker(object):
	pass

class NewNoteBodyTable(table.SequenceTable):
	pass

@component.adapter( nti_interfaces.IUser, nti_interfaces.IStreamChangeEvent )
def user_change_new_note_emailer( user, change ):
	"""
	For incoming shared objects that are notes being freshly created,
	attempts to email them
	"""

	if change.type != nti_interfaces.SC_CREATED:
		return

	change_object = change.object
	if not nti_interfaces.INote.providedBy( change_object ):
		return

	profile = user_interfaces.IUserProfile( user )
	email = getattr( profile, 'email', None )
	opt_in = getattr( profile, 'opt_in_email_communication', True )
#	if not email or not opt_in:
#		email = 'jason.madden@nextthought.com'
#		opt_in = True
	if not email or not opt_in:
		logger.debug( "User %s has no email (%s) or hasn't opted in (%s), no way to send notices",
					  user, email, opt_in )
		return


	# Ok, now here's the tricky part. Until we have preferences or something about who/how to send
	# email, we're doing something a bit weird. We still want to be able to configure this, possibly
	# in site.zcml. We think we only want to do this for a very small handful of users. So the easy
	# thing to do is look up a named utility. We will use the username. We could also
	# use the groups the user belongs to in the same way acls do, or we could even look for
	# sites
	request = get_current_request()
	names = [user.username] + list(site_policies.get_possible_site_names( request=request, include_default=True ))
	send = False
	for name in names:
		if component.queryUtility( ITemporaryChangeEmailMarker, name=name ):
			send = True
			logger.debug( "Sending change email to %s due to configuration at %r", user, name )
			break
	if send:
		base_template = 'note_created_email'

		the_table = NewNoteBodyTable( [change_object],
									  PyramidZopeRequestProxy( request ) if request else None )

		the_table.update()

		queue_simple_html_text_email(
			base_template, subject="New Note Created",
			recipients=[email],
			template_args={'note': change_object,
						   'change': change,
						   'user': user,
						   'note_table': the_table,
						   'note_text': '\n'.join( component.queryAdapter( x, frg_interfaces.IPlainTextContentFragment, name='text', default='' ) for x in change_object.body ),
						   'profile': profile},
			request=request	)
