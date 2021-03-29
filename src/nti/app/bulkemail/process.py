#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import zlib
try:
	import cPickle as pickle
except ImportError:
	import pickle

import boto3

from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.publisher.interfaces.browser import IBrowserRequest

from nti.base._compat import text_

from nti.common._compat import sleep

from nti.dataserver.interfaces import IRedisClient

from nti.mailer.interfaces import ITemplatedMailer

from nti.zodb.tokenbucket import PersistentTokenBucket

from .interfaces import PreflightError
from .interfaces import IBulkEmailProcessLoop
from .interfaces import IBulkEmailProcessMetadata
from .interfaces import IBulkEmailProcessDelegate

#: The redis lifetime of the objects used during the sending
#: process. Should be long enough for the process to complete,
#: but not too long to avoid clutter
_TTL = 14 * 24 * 60 * 60 * 60 # two weeks

#: Default for the maximum number of emails we'll send to Amazon SES per
#: second.  Should only come into play if fetching the quota fails, e.g.
#: if many bulk processes are kicked off at once.
DEFAULT_SES_SEND_RATE = 14

#: AWS error code for throttling failures, e.g. exceeding max messages
#: per second or per day
EC_THROTTLING = 'Throttling'

#: AWS error messages for specific throttling conditions
MESSAGE_QUOTA_EXCEEDED = 'Daily message quota exceeded.'
SENDING_RATE_EXCEEDED = 'Maximum sending rate exceeded.'


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

@interface.implementer(IBulkEmailProcessMetadata)
class _RedisProcessMetaData(object):

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

from nti.appserver.policies.site_policies import find_site_policy

@interface.implementer(IBulkEmailProcessLoop)
class DefaultBulkEmailProcessLoop(object):

	#: The amount of time for which we will hold the lock during
	#: processing of one email to send.
	#: This is a tradeoff between being able to recover from dead
	#: instances and being sure that we can finish the processing
	lock_timeout = 60 * 10 # ten minutes

	#: If set to true, then we will include the current site name (if any)
	#: in the process names in redis. This is useful if the process
	#: needs to run for each site hosted in the same database.
	include_site_names = False

	request = None

	__name__ = None
	__parent__ = None

	def __init__( self, request ):
		# For purposes of templates and translation, proxy the
		# pyramid request to a zope request
		self.request = IBrowserRequest(request)
		self.redis = component.getUtility( IRedisClient )

	@Lazy
	def names(self):
		name = self.__name__
		if self.include_site_names:
			policy, policy_name = find_site_policy()
			if policy is not None and policy_name:
				name = name + '/' + policy_name
		return _ProcessNames(name)

	@Lazy
	def metadata(self):
		return _RedisProcessMetaData(self.redis, self.names.metadata_name)

	@Lazy
	def lock(self):
		return self.redis.lock( self.names.lock_name, self.lock_timeout )

	@Lazy
	def delegate(self):
		return component.getMultiAdapter( (self, self.request),
										  IBulkEmailProcessDelegate,
										  name=self.__name__)

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

		XXX: This may fail if we retry due to a conflict (storing user time
		metadata in digest_email.py). The emails *should* have been sent
		successfully though. Unfortunately, since the time metadata is
		rolled back. The user will get duplicate notables the next time
		this process runs. This occurred due to multiple digest jobs running
		in close proximity to one another.
		"""
		for name in self.names.names:
			if self.redis.exists(name):
				raise PreflightError(name)

		try:
			getattr(self, 'delegate')
		except LookupError:
			raise PreflightError("Failed to find delegate")

	def reset_process(self):
		"""
		Reset the process back to initial conditions.
		"""
		self.redis.delete( *self.names.names )

	@Lazy
	def throttle(self):
		# To respect the SES limits, but leave headroom for other processes
		# we send at limited rates in burst and fill slower than that.
		# TODO: These heuristics can be better, especially for the higher
		# max send rate.
		# NOTE: We are not handling the daily quota other than by exceptions
		# Derive a value for the throttle.
		# For a send-rate of 14, this gives ~6.1, for 5 it gives ~2.2
		val = self.max_send_rate
		# Token buckets removed in whole numbers, minimum 1
		burst_rate = max((val/2.3), 1.0)
		# For send-rate of 14 this gives ~4.7, for 5 it gives ~1.7
		fill_rate = (val/3)
		return PersistentTokenBucket( burst_rate, fill_rate=fill_rate )

	@Lazy
	def max_send_rate(self):
		try:
			return self.client.get_send_quota()['MaxSendRate']
		except Exception:
			return DEFAULT_SES_SEND_RATE

	def _aws_session(self):
		return boto3.session.Session()

	@Lazy
	def client(self):
		return self._aws_session().client('ses')

	@Lazy
	def mailer(self):
		return component.getUtility(ITemplatedMailer)

	def initialize(self):
		"""
		Prep the process for starting. Preflight it, then collect all the
		recipients needed.
		"""

		self.preflight_process()
		logger.info( "Beginning process for %s", self.__name__ )

		self.metadata.startTime = time.time()
		self.metadata.status = 'Started'
		self.metadata.save()

		count = self.add_recipients( self.delegate.collect_recipients() )
		logger.info( "Collected %d recipients", count )

	def add_recipients( self, recipient_data ):
		"""
		Save the given recipient data, validating each one.
		"""

		values = []
		for recipient in recipient_data:
			if 'email' not in recipient or not recipient['email']:
				raise ValueError('missing email')
			values.append( zlib.compress( pickle.dumps( recipient, pickle.HIGHEST_PROTOCOL ) ) )

		if values:
			self.redis.sadd( self.names.source_name, *values )
			self.redis.expire( self.names.source_name, _TTL )

		return len(values)

	def process_one_recipient( self ):
		"""
		Generally called outside of a transaction to send an email.

		If you need a transaction and/or site configured, you will
		need to subclass this process and begin your transaction
		around either this method (for fine-grained scope) or around
		:meth:`process_loop` (for bulk scope). Typically you will be better
		off establishing the transaction around this method, and aborting
		it when the transaction returns. In this way you ensure that the data
		is self-consistent for a single email.

		:return: ``None`` if there are no more recipients. Otherwise,
			the (true-ish) value of sending the email.
		"""

		delegate = self.delegate
		with self.lock:
			member = self.redis.srandmember( self.names.source_name )
			if member is None:
				# Done!
				return None

			recipient_data = pickle.loads(zlib.decompress(member))

			fromaddr = delegate.compute_fromaddr_for_recipient( recipient_data )
			sender = delegate.compute_sender_for_recipient( recipient_data )

			# Probably if there were `template_args` and this method
			# returns None, we should not send to this client: something
			# changed behind our back. We should record a failure and keep going
			template_args = delegate.compute_template_args_for_recipient(recipient_data)

			result = {'SendEmailResult': 'Not sent'}
			if sender is not None and template_args is not None:
				pmail_msg = self.mailer.create_simple_html_text_email(
					self.delegate.template_name,
					subject=delegate.compute_subject_for_recipient(recipient_data),
					request=self.request,
					recipients=[recipient_data['email']],
					template_args=template_args,
					text_template_extension=delegate.text_template_extension)

				pmail_msg.sender = fromaddr
				mail_msg = pmail_msg.to_message()
				msg_string = mail_msg.as_string()

				# Now send the email. This might raise SESError or its subclasses. If it does,
				# sending failed and we exit, having left the recipient still on the source list.
				result = self.client.send_raw_email(
					RawMessage={
						'Data': msg_string
					},
					Source=sender,
					Destinations=[pmail_msg.recipients[0]])

				# Result will be something like:
				# { 'ResponseMetadata': {'RetryAttempts': 0, 'HTTPStatusCode': 200,
				# 					  'RequestId': 'b93196c1-6872-4d94-8f9f-6245571f2461',
				# 					  'HTTPHeaders': {'date': 'Thu, 25 Mar 2021 05:00:06 GMT',
				# 									  'x-amzn-requestid': 'b93196c1-6872-4d94-8f9f-6245571f2461',
				# 									  'content-length': '338', 'content-type': 'text/xml',
				# 									  'connection': 'keep-alive'}},
				#   u'MessageId': '011f017867c1071d-edd2eda1-fdec-4a45-b7bf-06d921c5e5e5-000000' }

			# Record the result and remove the need to send again
			self.redis.srem( self.names.source_name, member )
			recipient_data.pop('template_args', None) # no need to repickle this
			recipient_data['boto.ses.result'] = result
			self.redis.sadd( self.names.dest_name, pickle.dumps( recipient_data,
																 pickle.HIGHEST_PROTOCOL ) )
			self.redis.expire( self.names.dest_name, _TTL )

			return result

	def process_loop( self ):
		"""
		Generally called outside of a transaction to send all the emails.

		If you need a transaction and/or site configured, you will
		need to subclass this process and begin your transaction
		around either this method (for bulk scope) or around
		:meth:`process_one_recipient` (for fine-grained scope). The
		latter is recommended, otherwise it is likely that, for a long
		process, by the end of the run, the data is inconsistent with
		the data at the beginning of the process.
		"""
		assert self.metadata.status != 'Completed'

		while True:
			self.throttle.wait_for_token()
			try:
				result = self.process_one_recipient()
			except ClientError as e:  #pragma: no cover
				error = e.response.get('Error')
				code = error.get('Code') if error is not None else None
				if code != EC_THROTTLING:
					logger.exception("ClientError while sending email")
					self.handle_abort(e)
					return

				message = error.get('Message') if error is not None else None
				if message not in (SENDING_RATE_EXCEEDED, MESSAGE_QUOTA_EXCEEDED):
					# XXX: Unexpected, unhandled.
					logger.exception("Unhandled throttling error; stopping process.")
					self.handle_abort(e)
					return

				if message == SENDING_RATE_EXCEEDED:
					logger.warn("Max sending rate exceeded; pausing: %s", e)
					sleep(10)  # arbitrary sleep time
					continue

				assert message == MESSAGE_QUOTA_EXCEEDED
				logger.warn( "Max daily quota exceeded; stopping process. Resume later. %s", e )
				self.metadata.status = text_(e)
				self.metadata.save()
				return
			except (BotoCoreError,Exception) as e:
				logger.exception("Failed to send email for unknown reason")
				self.handle_abort(e)
				return

			if not result:
				break

		num_sent = self.redis.scard( self.names.dest_name )
		self.metadata.status = 'Completed'
		self.metadata.endTime = time.time()
		self.metadata.save()

		logger.info( "Completed sending %s to %s recipients", self.__name__, num_sent )

	def handle_abort(self, exception):
		self.metadata.status = text_(exception)
		self.metadata.save()
		try:
			del self.client
		except AttributeError:
			pass


from nti.dataserver.interfaces import IDataserverTransactionRunner

class SiteTransactedBulkEmailProcessLoop(DefaultBulkEmailProcessLoop):
	"""
	A process that establishes a database connection and a ZCA SiteManager
	around the processing of each recipient. Because this uses the request
	and therefore implicitly the site, we include site names in our
	redis lock.
	"""

	include_site_names = True

	def __init__(self, request):
		super(SiteTransactedBulkEmailProcessLoop,self).__init__(request)
		self.possible_site_names = request.possible_site_names
		self._super_process_one_recipient = super(SiteTransactedBulkEmailProcessLoop,self).process_one_recipient

	@Lazy
	def _runner(self):
		return component.getUtility(IDataserverTransactionRunner)

	def process_one_recipient(self):
		return self._runner(self._super_process_one_recipient,
							site_names=self.possible_site_names,
							job_name=text_(self.__name__),
							side_effect_free=True)
