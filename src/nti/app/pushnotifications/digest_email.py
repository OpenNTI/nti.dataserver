#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for building digest emails.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface
from zope import component

from pyramid.traversal import find_interface

from nti.dataserver.interfaces import IUser
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.app.notabledata.interfaces import IUserNotableData
from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import EmailAddresablePrincipal
from nti.contentfragments.interfaces import IPlainTextContentFragment
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.dataserver.interfaces import INote
from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.interfaces import IStreamChangeEvent
from nti.appserver.interfaces import IVideoIndexMap

import time

from nti.utils.property import annotation_alias
from nti.utils.property import Lazy

from nti.app.bulkemail.delegate import AbstractBulkEmailProcessDelegate

_ONE_WEEK = 7 * 24 * 60 * 60
_TWO_WEEKS = _ONE_WEEK * 2
_ONE_MONTH = _TWO_WEEKS * 2
_TWO_MONTH = _ONE_MONTH * 2

class _TemplateArgs(object):

	def __init__(self, values, request):
		self._primary = values[0]
		self.request = request
		self.remaining = len(values) - 1

	def __getattr__(self, name):
		return getattr(self._primary, name)

	@Lazy
	def __parent__(self):
		return _TemplateArgs([self._primary.__parent__],
							 self.request)

	@Lazy
	def course(self):
		from nti.contenttypes.courses.interfaces import ICourseInstance
		course = ICourseInstance(self._primary, None)
		if course is None:
			course = find_interface(self._primary, ICourseInstance)
		if course is not None:
			return _TemplateArgs([course],
								 self.request)

	@Lazy
	def assignment_name(self):
		from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem
		item = find_interface(self._primary, IUsersCourseAssignmentHistoryItem)
		asg_id = None
		if item is not None:
			asg_id = item.assignmentId
		else:
			# We could be a grade
			asg_id = getattr(getattr(self._primary, 'object', None), 'AssignmentId', None)

		if asg_id is not None:
			from nti.assessment.interfaces import IQAssignment
			asg = component.queryUtility(IQAssignment, name=asg_id)
			return getattr(asg, 'title', None)


	@property
	def snippet(self):
		if self._primary.body and isinstance(self._primary.body[0], basestring):
			text = IPlainTextContentFragment(self._primary.body[0])
			if len(text) > 30:
				text = text[:30] + '...'
			return text
		return ''


	@property
	def display_name(self):
		# TODO: Isn't there a zope interface for this? We would adapt
		# self._primary to IDisplayName or something?
		if self.__name__.startswith('tag:'):
			# Try to find a content unit
			lib = component.getUtility(IContentPackageLibrary)
			path = lib.pathToNTIID(self.__name__)
			if path:
				return path[-1].__name__

			# FIXME: Eww, ugly
			videos = component.getUtility(IVideoIndexMap)

			for key, value in videos.by_container.items():
				if self.__name__ in value:
					path = lib.pathToNTIID(key)
					if path:
						return path[-1].__name__
		return self.__name__

	@property
	def creator(self):
		names = IFriendlyNamed(self._primary.creator)
		return names.alias or names.realname

	@property
	def href(self):
		return self.request.resource_url(self._primary)

@component.adapter(IUser, interface.Interface)
class DigestEmailCollector(object):

	def __init__(self, context, request):
		self.remoteUser = context
		self.request = request


	_SENTKEY = 'nti.app.pushnotifications.digest_email.DigestEmailCollector.last_sent'
	last_sent = annotation_alias(_SENTKEY, annotation_property='remoteUser',
								 default=0,
								 doc="last_sent is stored as an annotation on the user")
	_COLLECTEDKEY = 'nti.app.pushnotifications.digest_email.DigestEmailCollector.last_collected'
	last_collected = annotation_alias(_COLLECTEDKEY, annotation_property='remoteUser',
								 default=0,
								 doc="last_sent is stored as an annotation on the user")

	@Lazy
	def collection_time(self):
		return time.time()

	def __call__(self):
		"""
		Returns a bulkemail \"recipient\" for the current user, if
		we should send a mail message.
		"""
		# If we have no email address on file, we can't send anything, obviously
		addr = IEmailAddressable(self.remoteUser,None)
		if not addr or not addr.email:
			return

		notable_data = component.getMultiAdapter( (self.remoteUser, self.request),
												  IUserNotableData)

		# Has anything notable happened since the user last checked?
		# Note that we place a bound of how far back into the past we
		# are willing to look; we're only going to show a few of the most
		# recent things anyway, but if the "most recent thing" is still weeks
		# old, that's actually not very interesting to the user and we don't need
		# to send them an email. We also track the last time we sent this email, too,
		# and don't resend if nothing interesting has happened since we last sent
		# the email...actually, we track the last time we checked; this lets
		# us be much more efficient in the (somewhat common) case that nothing
		# changes for the same user.

		last_time_collected = self.last_collected
		self.last_collected = self.collection_time
		# TODO: When should we update this? If we update it now, we risk not actually
		# sending the email. If we update it when we actually send, that turns a read
		# transaction into a write transaction. If we keep it in redis, we could reset
		# it easily enough but we need the hooks to do that...for now, we update
		# it when we collect recipients
		last_email_sent = self.last_sent
		last_viewed_data = notable_data.lastViewed
		historical_cap = self.collection_time -  _TWO_WEEKS

		min_created_time = max( last_email_sent, last_time_collected, last_viewed_data, historical_cap )

		notable_intids_since_last_viewed = notable_data.get_notable_intids(min_created_time=min_created_time)
		if not notable_intids_since_last_viewed:
			# Hooray, nothing to do
			logger.debug( "User %s/%s had 0 notable items since %s",
						  self.remoteUser, addr.email, min_created_time)

			return

		# We need to group them by type in order to provide group summaries,
		# but we only want to display the complete information
		# about the first (most recent) item in each group
		# TODO: There should be heuristics around that, it should be the
		# first, most notable, thing

		# So first we sort them by created time, descending.
		sorted_by_time = notable_data.sort_notable_intids(notable_intids_since_last_viewed,
														  reverse=True,
														  reify=True)

		# Then we can sort them by type, trusting the stable sort to preserve
		# relative creation times among items of the same type
		# (TODO: Is this actually guaranteed stable? If not we need our own stable implementation)
		sorted_by_type_time = notable_data.sort_notable_intids(sorted_by_time,
															   field_name='mimeType',
															   reify=True )

		logger.debug( "User %s/%s had %d notable items since",
					  self.remoteUser, addr.email, len(sorted_by_type_time), min_created_time)
		return {'email': EmailAddresablePrincipal(self.remoteUser),
				'template_args': sorted_by_type_time,
				'since': min_created_time}


	def recipient_to_template_args(self, recipient, request):
		# Now iterate to get the actual content objects
		# (Note that grade objects are going to have a `change` content type, which is
		# unique)
		sorted_by_type_time = recipient['template_args']

		notes = list()
		comments = list()
		topics = list()
		circled = list()
		grade = list()
		feedback = list()
		other = list()

		notable_data = component.getMultiAdapter( (self.remoteUser, self.request),
												  IUserNotableData)

		for o in notable_data.iter_notable_intids(sorted_by_type_time):
			if INote.providedBy(o):
				notes.append(o)
			elif ICommentPost.providedBy(o):
				comments.append(o)
			elif ITopic.providedBy(o):
				topics.append(o)
			elif IStreamChangeEvent.providedBy(o):
				if o.type == 'Circled':
					circled.append(o)
				else:
					grade.append(o)
			elif o.__class__.__name__ == 'UsersCourseAssignmentHistoryItemFeedback': # XXX FIXME: Coupling
				feedback.append(o)
			else:
				other.append(o)
		# Comments has multiple mime types, as does topics
		comments.sort(reverse=True,key=lambda x: x.createdTime)
		topics.sort(reverse=True,key=lambda x: x.createdTime)

		result = dict()
		for k, values in (('discussion', topics),
						  ('note', notes),
						  ('comment', comments),
						  ('feedback', feedback),
						  ('circled', circled),
						  ('grade', grade),
						  ('other', other)):
			if values:
				template_args = _TemplateArgs(values, request)
			else:
				template_args = None
			result[k] = template_args

		result['unsubscribe_link'] = request.resource_url(self.remoteUser, 'unsubscribe')
		return result



from nti.dataserver.interfaces import IDataserver
from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate

from nti.dataserver.users import User

@interface.implementer(IBulkEmailProcessDelegate)
class DigestEmailProcessDelegate(AbstractBulkEmailProcessDelegate):

	subject = _("Here's what you've missed")

	template_name = 'nti.app.pushnotifications:templates/digest_email'

	@Lazy
	def _dataserver(self):
		return component.getUtility(IDataserver)

	def _accept_user(self, user):
		return IUser.providedBy(user)

	def collect_recipients(self):
		users_folder = self._dataserver.users_folder
		now = time.time()
		for user in users_folder.values():
			if self._accept_user(user):
				collector = DigestEmailCollector(user, self.request)
				collector.collection_time = now
				possible_recipient = collector()
				if possible_recipient:
					collector.last_sent = time.time()
					yield possible_recipient

	def compute_template_args_for_recipient(self, recipient):
		user = User.get_user( recipient['email'].id, self._dataserver )
		# XXX If the user disappears, we're screwed.
		# We should also take care if some of the intids referenced disappear
		collector = DigestEmailCollector(user, self.request)

		return collector.recipient_to_template_args(recipient, self.request)


class DigestEmailProcessTestingDelegate(DigestEmailProcessDelegate):

	subject = _("TEST - Here's what you've missed")

	def _accept_user(self, user):
		if super(DigestEmailProcessTestingDelegate,self)._accept_user(user):
			email = getattr(IEmailAddressable(user, None), 'email', None)
			if email:
				if email.endswith('@nextthought.com'):
					return True
				if email == 'jamadden@ou.edu':
					return True

	def collect_recipients(self):
		for possible_recipient in super(DigestEmailProcessTestingDelegate,self).collect_recipients():
			# Reset the sent and collected times
			collector = DigestEmailCollector(User.get_user(possible_recipient['email'].id, self._dataserver),
											 self.request)
			collector.last_collected = collector.last_sent = 0


			logger.info( "User %s/%s had %d notable objects",
						 possible_recipient['email'].id, possible_recipient['email'].email,
						 len(possible_recipient['template_args']))
			#possible_recipient['email'].email = 'jason@nextthought.com'
			yield possible_recipient
