#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools and for dealing with bounced emails. Bounce notifications go
to an SQS queue where they are processed in batch by running the command
provided in this module. Permanent failures are found and correlated
to user accounts (with substantial logging). The user profile of these
accounts is updated to remove the email, since it is invalid (and continuing to get
bounces for it can make Amazon SES very angry), and links are added to the
user for the application to notice at the next logon time:


.. todo:: It might be possible for the server to detect the update events and
  automatically clear the link. I'm not sure.

.. todo:: The only thing the client can do with these links is DELETE them.
  Would it be useful for them to serve as PUT aliases to update the profile?
  That just seems to complicate the clint which already 'knows' how to update
  the profile (but it could be handy from the command line).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import argparse
import simplejson as json
from collections import defaultdict

import boto
from boto.sqs.message import RawMessage

from zope import component

from zope.interface.exceptions import Invalid

from nti.appserver.account_recovery_views import find_users_with_email

from nti.appserver.link_providers import flag_link_provider

from nti.appserver.logon import REL_INVALID_EMAIL
from nti.appserver.logon import REL_INVALID_CONTACT_EMAIL

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users.utils import unindex_email_verification

from nti.dataserver.utils import run_with_dataserver

from nti.mailer.interfaces import IVERP

def _unverify_email(user):
	IUserProfile( user ).email_verified = False
	unindex_email_verification(user)

def _mark_accounts_with_bounces( email_addrs_and_pids, dataserver=None ):
	"""
	Given a sequence of (email addresses, principal id, bounce_sub_type), find all the
	accounts that correspond to those addresses pairs, and take
	appropriate action.

	:return: A set of principal ids that were found and a set of all
		principal ids that were looked for.
	"""
	if not email_addrs_and_pids:
		return (), ()

	matched_pids = set()
	all_pids = set()

	dataserver = dataserver or component.getUtility( IDataserver )
	for email_addr, possible_pid, unused_bounce_subtype in email_addrs_and_pids:
		if possible_pid:
			all_pids.add(possible_pid)

		users = find_users_with_email(email_addr,
									  dataserver,
									  match_info=True,
									  require_can_login=False)
		if not users:
			logger.warn( "No users found associated with bounced email %s", email_addr )
			continue

		logger.info( "The following users are associated with the email address %s (looking for %s): %s",
					 email_addr, possible_pid or '', users )
		for user, match_type in users:
			if possible_pid:
				if user.username.lower() != possible_pid.lower():
					continue
			# Record the fact that we're going to flag this user,
			# even if we didn't get a VERP pid
			matched_pids.add(possible_pid or user.username)

			__traceback_info__ = user, match_type, email_addr
			if match_type == 'email':
				_unverify_email(user)
				flag_link_provider.add_link( user, REL_INVALID_EMAIL )
			elif match_type == 'password_recovery_email_hash':
				# Hmm. Can't really clear it, but this will never get to them
				# they probably can't logon
				_unverify_email(user)
				flag_link_provider.add_link( user, REL_INVALID_EMAIL )
			else:
				# all that's left is contact_email (which has two match types)
				flag_link_provider.add_link( user, REL_INVALID_CONTACT_EMAIL )

	return matched_pids, all_pids

import collections

ProcessResult = collections.namedtuple('ProcessResult',
									   ['processed_messages',
										'matched_messages',
										'transient_error_addrs',
										'permanent_error_addrs',
										'matched_pids'])

def process_ses_feedback(messages, dataserver=None, mark_transient=False):
	"""
	Given an iterable of :class:`boto.sqs.message.Message` objects
	that represent `feedback from SES <http://docs.amazonwebservices.com/ses/latest/DeveloperGuide/NotificationContents.html>`_,
	process them.

	:param bool mark_transient: If set to ``True`` (defaults to False) then
	   bounce notifications that are transient result in corresponding user
	   accounts being marked as needing an update. Transient email bounces
	   may be caused by something as simple as an "OutOfMessage" auto-reply.
	   Therefore, it is probably never correct to mark these messages as
	   requiring update.
	   https://docs.aws.amazon.com/ses/latest/DeveloperGuide/notification-contents.html#bounce-object


	:return: A tuple-like instance of :class:`ProcessResult`.
		The first element is a list of all the messages that were processed for bounce information.
		If a message wasn't processed because it wasn't a bounce notice, it won't be
		in this list. The second element is a list of messages that actually correlated
		with a user account using that email address. It is the caller's responsibility to delete
		(some subset of) these messages from the SQS queue if desired (once the transaction has committed safely).
	"""

	proc_messages = []
	addr_permanent_errors = set()
	addr_transient_errors = set()
	verp = component.getUtility(IVERP)
	pids_to_messages = defaultdict(list)

	i = 0
	for message in messages:
		body = message.get_body()
		try:
			body = json.loads( body )
		except (TypeError,ValueError): # pragma: no cover
			continue

		if body.get( 'Type' ) != 'Notification': # pragma: no cover
			continue
		try:
			body = json.loads( body['Message'] )
		except (TypeError,ValueError,KeyError): # pragma: no cover
			continue

		if body['notificationType'] != 'Bounce':
			continue

		i += 1
		proc_messages.append( message )
		bounce = body['bounce']
		errors = addr_permanent_errors if bounce['bounceType'] == 'Permanent' else addr_transient_errors

		# We'll only get a PID if we're in the right environment
		pids = verp.principal_ids_from_verp(body['mail']['source'])

		pid = pids[0] if pids else None
		if pid:
			pids_to_messages[pid].append(message)

		for bounced in bounce['bouncedRecipients']:
			errors.add( (bounced['emailAddress'], pid, bounce['bounceSubType']) )

	logger.info( "Processed %d bounce notices", i )
	logger.info( "The following email addresses experienced transient failures: %s", addr_transient_errors )
	logger.info( "The following email addresses experienced permanent failures: %s", addr_permanent_errors )

	to_mark = addr_permanent_errors
	if mark_transient:
		to_mark = to_mark.union( addr_transient_errors )

	matched_pids, _ = _mark_accounts_with_bounces( to_mark, dataserver=dataserver )
	logger.info( "Found the following users with failures: %s", matched_pids)

	matched_messages = list()
	for matched_pid in matched_pids:
		matched_messages.extend(pids_to_messages[matched_pid])

	return ProcessResult(proc_messages, matched_messages,
						 addr_transient_errors,
						 addr_permanent_errors,
						 matched_pids)

def process_sqs_queue(queue_name, delete_matched=True):
	"""
	Called from within the scope of a transaction/dataserver,
	connect to an SQS queue, poll for all messages and then
	use :func:`process_ses_feedback`.

	:keyword delete_matched: If `True` (the default), then any
		messages we successfully correlated to principals will
		be removed from the SQS queue. Because of VERP, this is safe
		to do even when multiple environments share the same
		SQS queue. This is done in a broad-reaching ``except``
		block so as to not interfere with committing the transaction.
	"""

	sqs = boto.connect_sqs()
	fb_q = sqs.get_queue( queue_name )
	fb_q.message_class = RawMessage  # These aren't encoded
	logger.info( "Processing bounce notices from %s", fb_q )
	def gen():
		while True:
			msgs = fb_q.get_messages(num_messages=10, # 10 is the max
									 wait_time_seconds=10)
			if not len(msgs):
				break

			for msg in msgs:
				yield msg

	result = process_ses_feedback( gen() )

	if delete_matched and result.matched_messages:
		# We only want to actually remove messages where
		# this environment had valid VERP data; even if we found
		# identical email addresses, we're not the canonical location
		# so later processes need to get a look.
		# (Likewise, if we are the canonical location and we do
		# remove it, it's probably ok if the address was also
		# used in an another environment---most likely it's testing,
		# not real-world use)
		# Max batch size is 10
		def _batch(messages, batch_size=10):
			start = 0
			while start < len(messages):
				yield messages[start: start+batch_size]
				start += batch_size

		for messages in _batch(result.matched_messages):
			try:
				resp = fb_q.delete_message_batch(messages)
				if resp.errors:
					logger.error("Failed to delete messages: %s", resp.errors)
			except Exception:
				logger.error("Failed to delete some messages")

	return result

def process_sqs_messages():
	"""
	A command-line tool to initiate SQS processing.

	.. note:: This is deprecated because it doesn't have access to the correct
		VERP context.
	"""
	arg_parser = argparse.ArgumentParser( description="Read SES feedback messages from an SQS queue and mark users that need updates." )
	arg_parser.add_argument( 'queue',
                             help="The SQS queue to read from. Default: %(default)s",
                              default='SESFeedback', nargs='?' )
	arg_parser.add_argument( '--env_dir',
                             help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose',
                             help="Be verbose", action='store_true',
                             dest='verbose')
	arg_parser.add_argument( '--delete',
                             help="After successful processing, delete messages that actually matched a user from SQS queue. Default: %(default)s",
							 action='store',
                             dest='delete',
                             default=True)

	args = arg_parser.parse_args()

	env_dir = _get_env_dir( args.env_dir )

	run_with_dataserver( environment_dir=env_dir,
						 function=lambda: process_sqs_queue(args.queue, args.delete),
						 xmlconfig_packages=('nti.appserver',),
						 verbose=args.verbose )

def mark_emails_bounced():
	"""
	A command-line testing tool to mark accounts using email addresses
	invalid.
	"""
	arg_parser = argparse.ArgumentParser( description="Search for accounts using an email address and mark them invalid." )
	arg_parser.add_argument( 'addrs', help="The email addresses to find.", nargs='+' )
	arg_parser.add_argument( '--env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')

	args = arg_parser.parse_args()

	def _proc():
		return _mark_accounts_with_bounces( args.addrs )

	env_dir = _get_env_dir( args.env_dir )

	run_with_dataserver( environment_dir=env_dir,
						 function=_proc,
						 xmlconfig_packages=('nti.appserver',),
						 verbose=args.verbose )

def _get_env_dir(env_dir):
	result = env_dir
	if not result:
		result = os.getenv( 'DATASERVER_DIR' )
	if not result or not os.path.exists(result) and not os.path.isdir(result):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	return result
