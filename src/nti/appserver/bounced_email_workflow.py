#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools and views for dealing with bounced emails. Bounce notifications go
to an SQS queue where they are processed in batch by running the command
provided in this module. Permanent failures are found and correlated
to user accounts (with substantial logging). The user profile of these
accounts is updated to remove the email, since it is invalid (and continuing to get
bounces for it can make Amazon SES very angry), and links are added to the
user for the application to notice at the next logon time:

.. py:data:: REL_INVALID_EMAIL

	The link relationship type (``state-bounced-email``) that
	indicates we know that the email recorded for this user is bad and
	has received permanent bounces. The user must be asked to enter a
	new one and update the profile. Send an HTTP DELETE to this link
	when you are done updating the profile to remove the flag.

.. py:data:: REL_INVALID_CONTACT_EMAIL

	The link relationship type (``state-bounced-contact-email``) that
	indicates that a contact email (aka parent email) recorded for
	this (under 13) user has received permanent bounces. The child
	must be asked to enter a new contact_email and update the profile.
	When the profile is updated, a new consent email will be
	generated. Send an HTTP DELETE to this link with you are done
	updating the profile to remove the flag.

.. note:: It might be possible for the server to detect the update events and
  automatically clear the link. I'm not sure.

.. note:: The only thing the client can do with these links is DELETE them.
  Would it be useful for them to serve as PUT aliases to update the profile?
  That just seems to complicate the clint which already 'knows' how to update
  the profile (but it could be handy from the command line).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

REL_INVALID_EMAIL = 'state-bounced-email'
REL_INVALID_CONTACT_EMAIL = 'state-bounced-contact-email'

import anyjson as json
import argparse
import boto
import boto.sqs.message

from zope import component

from pyramid.view import view_config

from nti.appserver import user_link_provider
from nti.appserver.user_link_provider import AbstractUserLinkDeleteView
from nti.appserver.account_recovery_views import find_users_with_email

from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.utils import run_with_dataserver

class BouncedEmailDeleteView(AbstractUserLinkDeleteView):

	LINK_NAME = REL_INVALID_EMAIL

	@view_config(name=REL_INVALID_EMAIL)
	def __call__( self ):
		return AbstractUserLinkDeleteView.__call__( self )


class BouncedContactEmailDeleteView(AbstractUserLinkDeleteView):

	LINK_NAME = REL_INVALID_CONTACT_EMAIL

	@view_config(name=REL_INVALID_CONTACT_EMAIL)
	def __call__( self ):
		return AbstractUserLinkDeleteView.__call__( self )

def process_ses_feedback( messages, dataserver=None, delete=True ):
	"""
	Given an iterable of :class:`boto.sqs.message.Message` objects
	that represent `feedback from SES <http://docs.amazonwebservices.com/ses/latest/DeveloperGuide/NotificationContents.html>`_,
	process them. When they have been successfully processed, remove them from the queue.
	"""

	proc_messages = []
	addr_permanent_errors = set()
	addr_transient_errors = set()
	i = 0
	for message in messages:
		body = message.get_body()
		try:
			body = json.loads( body )
		except (TypeError,ValueError):
			continue

		if body.get( 'Type' ) != 'Notification':
			continue
		try:
			body = json.loads( body['Message'] )
		except (TypeError,ValueError,KeyError):
			continue

		if body['notificationType'] != 'Bounce':
			continue
		i += 1
		bounce = body['bounce']
		errors = addr_permanent_errors if bounce['bounceType'] == 'Permanent' else addr_transient_errors

		for bounced in bounce['bouncedRecipients']:
			errors.add( bounced['emailAddress'] )

		proc_messages.append( message )

	logger.info( "Processed %d bounce notices", i )
	logger.info( "The following email addresses experienced transient failures: %s", addr_transient_errors )
	logger.info( "The following email addresses experienced permanent failures: %s", addr_permanent_errors )
	dataserver = dataserver or component.getUtility( nti_interfaces.IDataserver )
	for email_addr in addr_permanent_errors:
		users = find_users_with_email( email_addr, dataserver, match_info=True )
		if not users:
			logger.warn( "No users found associated with bounced email %s", email_addr )
			continue

		logger.info( "The following users are associated with the email address %s: %s", email_addr, users )
		for user, match_type in users:
			if match_type == 'email':
				# Clear it
				user_interfaces.IUserProfile( user ).email = None
				user_link_provider.add_link( user, REL_INVALID_EMAIL )
			elif match_type == 'password_recovery_email_hash':
				# Hmm. Can't really clear it, but this will never get to them
				# they probably can't logon
				user_link_provider.add_link( user, REL_INVALID_EMAIL )
			else:
				# all that's left is contact
				user_link_provider.add_link( user, REL_INVALID_CONTACT_EMAIL )

	if delete:
		for msg in proc_messages:
			msg.delete()

	return proc_messages

def process_sqs_messages():
	arg_parser = argparse.ArgumentParser( description="Create a user-type object" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'queue', help="The SQS queue to read from" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')


	args = arg_parser.parse_args()

	def _proc():
		sqs = boto.connect_sqs()
		fb_q = sqs.get_queue( args.queue )
		fb_q.message_class = boto.sqs.message.RawMessage
		logger.info( "Processing bounce notices from %s", fb_q )
		def gen():
			msg = fb_q.read()
			while msg is not None:
				yield msg
				msg = fb_q.read()
		return process_ses_feedback( gen(), delete=False )

	env_dir = args.env_dir
	proc_msgs = run_with_dataserver( environment_dir=env_dir,
									 function=_proc,
									 xmlconfig_packages=('nti.appserver',),
									 verbose=args.verbose )

	# If we got through without a transaction error, then we can delete the messages
	#....
	#for msg in proc_msgs:
	#	msg.delete()
