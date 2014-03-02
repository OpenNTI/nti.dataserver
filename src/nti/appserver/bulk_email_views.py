#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for the sending of bulk emails using `Amazon SES`_.

General Comments
================

The sending of bulk or mass emails is different than the sending of
individual email in a few important ways, mostly related to spam
blocking and the handling of bounced or undeliverable email.

Fighting Spam
-------------

Because of the volume and the standardized text of these emails, they
are more likely to be classified as spam than individual emails. To that
end, we must be sure to take special steps to help avoid that, not only
for the bulk email, but to prevent follow-on effects from damaging the spam
scores applied to our entire domain. These steps include:

* Being sure that DKIM is used for the domain sending email (easily done with
  `SES and Route 53 <http://docs.aws.amazon.com/ses/latest/DeveloperGuide/dkim.html>`_);
* Setting up `SPF <http://openspf.org>`_ for the domain sending email
  (also easily done with `SES and Route 53 <http://docs.aws.amazon.com/ses/latest/DeveloperGuide/spf.html>`_
  --- note that the ``Return-Path`` header is set by SES, no matter if using the SMTP
  or HTTP interface, to an ``amazonses.com`` address, and it is this
  domain that is verified for SPF);
* Using a separate domain for the ``From`` address so as to not "poison"
  the primary domain in spam rankings (in this case, ``alerts.nextthought.com``).

Bounces and Tracking
--------------------

To better be able to understand and track the bounce behaviour of bulk emails,
and to be able to independently control our reaction to bounces (e.g., whether
or not to force users to reset email addresses) we take two important steps.

First, we configure SES to use a separate `Amazon SNS`_ topic for the domain
sending bulk emails. We call this topic ``BulkSESFeedback``, and it feeds a
`Amazon SQS`_ queue also called ``BulkSESFeedback.`` This queue can be polled for
messages separately from ``SESFeedback`` and it may or may not be configured to
send email alerts.

Second, for each email we send, we use a distinct ``From`` address, encoding
some information about the target and purpose of the email. The exact format
is TBD.

Process
=======

The basic outline of the process is as follows.

#. In a transaction, gather the set of email addresses to send bulk email to:

	* This may or may not include additional information needed in the email template;
	  if it does, it means the remainder of the process is entirely independent of
	  the database
	* Put this information in a specially named Redis set; also
	  put some metadata related to the process in Redis.

#. Next, not in a transaction and probably in a background greenlet:

	* Pop an item off the Redis source set
	* Construct the email using the desired templates
	* Use Boto's support for SES to send the raw message; note that this is
	  not done with either :mod:`pyramid_mailer` or :mod:`repoze.sendmail`
	* Place the item from the source set, along with the tracking information
	  from the SES result, in a Redis destination set.
	* Throttle

The use of the raw SES API is important as we must be careful to stay within
the SES rate limits, which restricts us to sending no more than 5 emails
a second (and 10,000 emails in a day). If we were queuing to :mod:`repoze.sendmail`,
the queue processor might try to send too many messages too fast and there
is no way to control that. (However, the flip side is that if this
process is consuming the full rate limit, the background queue processor might
fail, so we have to be conservative.)

.. note::
	We will limit the second step to being non-concurrent
	through Redis locks. In order to properly use the template system
	it will run within a configured application worker (using a
	background greenlet)

Transparency
============

The use of the two Redis sets is designed to allow for monitoring and
resumability. A status page can:

* Show the count of messages sent and still to send;
* Allow initiating the entire process;
* Allow starting a sending process (step two);
* Allow resetting both queues so the process can be re-initiated

.. _Amazon SES: http://aws.amazon.com/documentation/ses/
.. _Amazon SNS: http://aws.amazon.com/documentation/sqs/
.. _Amazon SQS: http://aws.amazon.com/documentation/sns/

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from datetime import datetime
import isodate
import anyjson as json
import gevent

import boto.ses
from boto.ses.exceptions import SESDailyQuotaExceededError
from boto.ses.exceptions import SESMaxSendingRateExceededError
from boto.ses.exceptions import SESAddressBlacklistedError
from boto.ses.exceptions import SESError

from zope import component
from zope.cachedescriptors.property import Lazy
from zope.catalog.interfaces import ICatalog

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index

from nti.utils._compat import sleep

from nti.zodb.tokenbucket import PersistentTokenBucket

from nti.mailer.interfaces import ITemplatedMailer

from . import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

#: The redis lifetime of the objects used during the sending
#: process. Should be long enough for the process to complete,
#: but not too long to avoid clutter
_TTL = 14 * 24 * 60 * 60 * 60 # two weeks

class _ProcessNames(object):
	"""
	Storage for the various Redis key names used during the sending process.
	These are all derived based on the template name being sent.
	"""

	def __init__( self, template_name ):
		base = 'var/bulk_emails/' + template_name
		self.lock_name = base + '/Lock'
		self.metadata_name = base + '/MetaData'
		self.source_name = base + '/SourceSet'
		self.dest_name = base + '/ResultSet'

		self.names = list(self.__dict__.values())

class _ProcessMetaData(object):

	startTime = 0
	endTime = 0
	status = ''

	def __init__( self, redis, name ):
		self._redis = redis
		self.__name__ = name

		hval = redis.hgetall( self.__name__ )
		if hval:
			self.startTime = float(hval['startTime'])
			self.endTime = float(hval['endTime'])
			self.status = hval['status']

	def save(self):
		self._redis.hmset( self.__name__,
						   {'startTime': self.startTime,
							'endTime': self.endTime,
							'status': self.status} )
		self._redis.expire( self.__name__, _TTL )

class _PreflightError(Exception):
	pass

class _Process(object):

	subject = "<No Subject>"

	#: The amount of time for which we will hold the lock during
	#: processing of one email to send.
	#: This is a tradeoff between being able to recover from dead
	#: instances and being sure that we can finish the processing
	lock_timeout = 60 * 10 # ten minutes

	request = None

	def __init__( self, template_name ):
		self.template_name = template_name
		self.redis = component.getUtility( nti_interfaces.IRedisClient )
		self.names = _ProcessNames( template_name )
		self.metadata = _ProcessMetaData( self.redis, self.names.metadata_name )
		# To respect the SES limits, but leave headroom for other processes
		# we send at most three per second in burst, steady state of one per second
		# NOTE: We are not handling the daily quota other than by exceptions
		self.throttle = PersistentTokenBucket( 3 )

		self.lock = self.redis.lock( self.names.lock_name, self.lock_timeout )

	@property
	def delivered_count(self):
		return self.redis.scard( self.names.dest_name )
	@property
	def remaining_count(self):
		return self.redis.scard( self.names.source_name )

	def preflight_process(self):
		"""
		Check that the process is in a state to be initially started, raising
		an exception if not. This checks that none of the objects meant to be
		in redis are.
		"""
		for name in self.names.names:
			if self.redis.exists(name):
				raise _PreflightError(name)

	def reset_process(self):
		"""
		Reset the process back to initial conditions.
		"""
		self.redis.delete( *self.names.names )

	@Lazy
	def sesconn(self):
		return boto.ses.connect_to_region( 'us-east-1' )

	@Lazy
	def mailer(self):
		return component.getUtility(ITemplatedMailer)

	def add_recipients( self, *recipient_data ):
		"""
		Save the given recipient data.

		:param recipient_data: A dict containing JSON-encodable values. Must have one key,
			``email`` containing a string of the email address. May optionally have
			a key ``template_args`` which itself is a JSON-encodable dictionary.
		"""

		values = []
		for recipient in recipient_data:
			if 'email' not in recipient or not recipient['email']:
				raise ValueError('missing email')
			values.append( json.dumps( recipient ) )

		self.redis.sadd( self.names.source_name, *values )
		self.redis.expire( self.names.source_name, _TTL )

	def compute_sender_for_recipient( self, recipient ):
		# TBD
		return 'no-reply@alerts.nextthought.com'

	def process_one_recipient( self ):
		"""
		Generally called outside of a transaction to send an email.

		:return: ``None`` if there are no more recipients. Otherwise,
			the (true-ish) value of sending the email.

		"""

		with self.lock:
			member = self.redis.srandmember( self.names.source_name )
			if member is None:
				# Done!
				return None

			recipient_data = json.loads(member)

			sender = self.compute_sender_for_recipient( recipient_data )

			pmail_msg = self.mailer.create_simple_html_text_email(
				self.template_name,
				subject=self.subject,
				request=self.request,
				recipients=[recipient_data['email']],
				template_args=recipient_data.get('template_args') )

			pmail_msg.sender = sender
			mail_msg = pmail_msg.to_message()
			msg_string = mail_msg.as_string()

			# Now send the email. This might raise SESError or its subclasses. If it does,
			# sending failed and we exit, having left the recipient still on the source list.
			# The one exception is if the address is blacklisted, that still counts as
			# success and we need to take him off the source list
			try:
				result = self.sesconn.send_raw_email( msg_string, sender, recipient_data['email'] )
			except SESAddressBlacklistedError as e: #pragma: no cover
				logger.warn("Blacklisted address: %s", e )
				result = {'SendEmailResult': 'BlacklistedAddress'}
			# Result will be something like:
			# {u'SendEmailResponse': {u'ResponseMetadata': {u'RequestId': u'a38159e2-b033-11e2-9c3f-dba8231cfdfd'},
			#  u'SendEmailResult':   {u'MessageId': u'0000013e51f5c299-5998b51c-ee6e-4b61-b7e8-443895b6dfb4-000000'}}}

			# Record the result and remove the need to send again
			self.redis.srem( self.names.source_name, member )
			recipient_data['boto.ses.result'] = result
			self.redis.sadd( self.names.dest_name, json.dumps( recipient_data ) )
			self.redis.expire( self.names.dest_name, _TTL )

			return result

	def process_loop( self ):
		"""
		Generally called outside of a transaction to send all the emails.
		"""
		assert self.metadata.status != 'Completed'

		while True:
			self.throttle.wait_for_token()
			result = True
			try:
				result = self.process_one_recipient()
			except SESMaxSendingRateExceededError as e: #pragma: no cover
				logger.warn( "Max sending rate exceeded; pausing: %s", e )
				sleep( 10 ) # arbitrary sleep time
			except SESDailyQuotaExceededError as e:
				logger.warn( "Max daily quota exceeded; stopping process. Resume later. %s", e )
				self.metadata.status = unicode(e)
				self.metadata.save()
				return
			except (SESError,Exception) as e:
				logger.exception( "Failed to send email for unknown reason" )
				self.metadata.status = unicode(e)
				self.metadata.save()
				try:
					del self.sesconn
				except AttributeError:
					pass
				return

			if not result:
				break

		num_sent = self.redis.scard( self.names.dest_name )
		self.metadata.status = 'Completed'
		self.metadata.endTime = time.time()
		self.metadata.save()

		logger.info( "Completed sending %s to %s recipients", self.template_name, num_sent )

class _PolicyChangeProcess(_Process):

	subject = 'Updates to NextThought User Agreement and Privacy Policy'

	def initialize(self):
		"""
		Prep the process for starting. Preflight it, then collect all the
		recipients needed.
		"""

		self.preflight_process()
		logger.info( "Beginning process for %s", self.template_name )

		self.metadata.startTime = time.time()
		self.metadata.status = 'Started'
		self.metadata.save()

		recips = self.collect_recipients()
		logger.info( "Collected %d recipients", len(recips) )
		self.add_recipients( *recips )

	def collect_recipients(self):
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)

		email_ix = ent_catalog.get( 'email' )
		contact_email_ix = ent_catalog.get( 'contact_email' )

		# It is slightly non-kosher but it is fast and easy to access
		# the forward index for all the email values
		emails = set()
		emails.update( email_ix._fwd_index.keys() )
		emails.update( contact_email_ix._fwd_index.keys() )
		return [{'email': x} for x in emails]

class _PolicyChangeProcessTesting(_PolicyChangeProcess):
	"""
	Collects all the emails, but returns a fixed set of test emails.
	"""

	subject = 'TEST - ' + _PolicyChangeProcess.subject

	template_name = 'policy_change_email'

	def collect_recipients( self ):
		recips = super(_PolicyChangeProcessTesting,self).collect_recipients()
		logger.info( "Real recipient count: %d", len(recips) )
		logger.debug( "%s", recips )
		return [{'email': 'alpha-support@nextthought.com'},
				{'email': 'jason.madden@nextthought.com'},
				{'email': 'grey.allman@nextthought.com'}]

class _Status(object):
	"""
	For viewing status information, as passed
	to the renderer.
	"""

	def __init__( self, process ):
		self.process = process

	def __getattr__( self, name ):
		try:
			return getattr( self.process, name )
		except AttributeError:
			return getattr( self.process.metadata, name )

	def _time(self, name):
		startTime = getattr( self.metadata, name )
		if startTime:
			return isodate.datetime_isoformat( datetime.fromtimestamp(startTime) )

	def startTimeISO(self):
		return self._time('startTime')
	def endTimeISO(self):
		return self._time('endTime')

	def processRunning(self):
		# We use the existence of the lock 'file' as a proxy
		# to determine if the process loop is running somewhere
		return self.redis.exists( self.names.lock_name )

@view_defaults( route_name='objects.generic.traversal',
				name='bulk_email_admin',
				permission=nauth.ACT_MODERATE,
			  )
class _BulkEmailView(object):

	_greenlets = []

	_FACTORIES = {'policy_change_email': _PolicyChangeProcess,
				  'test_policy_change_email': _PolicyChangeProcessTesting}

	def __init__( self, request ):
		self.request = request
		self._name = None

	def _preflight(self):
		if not self.request.subpath or not self.request.subpath[0] in self._FACTORIES:
			raise hexc.HTTPNotFound()

		self._name = self.request.subpath[0]
		factory = self._FACTORIES[self._name]
		template_name = getattr( factory, 'template_name', None ) or self.request.subpath[0]

		if not component.getUtility(ITemplatedMailer).do_html_text_templates_exist(template_name):
			raise hexc.HTTPNotFound()

		process = factory(template_name)
		process.request = self.request
		return process

	@view_config(request_method='GET',
				 renderer='templates/bulk_email_admin.pt')
	def get(self):
		process = self._preflight()

		status = _Status( process )
		self.request.context = status
		# Use a dict to override the context argument that pyramid
		# directly inserts
		return {'context': status}

	@view_config(request_method='POST',
				 renderer='templates/bulk_email_admin.pt')
	def post(self):
		process = self._preflight()
		if 'subFormTable.buttons.resume' in self.request.POST:
			process.metadata.status = 'Resumed'
			process.metadata.save()
			greenlet = gevent.spawn( run=process.process_loop )
			# ICK. Must save this somewhere so it doesn't get
			# GC'd. Where?
			_BulkEmailView._greenlets.append( greenlet )
		elif 'subFormTable.buttons.initialize' in self.request.POST:
			# need to collect and then spawn the process
			process.initialize()
		elif 'subFormTable.buttons.start' in self.request.POST:
			# need to collect and then spawn the process
			process.initialize()
			greenlet = gevent.spawn( run=process.process_loop )
			# ICK. Must save this somewhere so it doesn't get
			# GC'd. Where?
			_BulkEmailView._greenlets.append( greenlet )
		elif 'subFormTable.buttons.reset' in self.request.POST:
			process.reset_process()

		# Redisplay the page with a get request to avoid the "re-send this POST?" problem
		get_path = self.request.path  + (('?' + self.request.query_string) if self.request.query_string else '')
		return hexc.HTTPFound(location=get_path)
