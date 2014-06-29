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

import time
import collections

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
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost
from nti.dataserver.interfaces import IStreamChangeEvent

from nti.appserver.interfaces import IApplicationSettings
from nti.contentlibrary.indexed_data.interfaces import IAudioIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer

from zc.displayname.interfaces import IDisplayNameGenerator

from nti.utils.property import Lazy
from nti.utils.property import annotation_alias

from nti.ntiids.ntiids import get_parts as parse_ntiid

from nti.app.bulkemail.delegate import AbstractBulkEmailProcessDelegate

from nti.externalization.oids import to_external_ntiid_oid

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
	def top_level_note(self):
		if self._primary.isOrWasChildInThread():
			return False
		return True

	@property
	def display_name(self):
		return component.getMultiAdapter((self._primary, self.request),
										 IDisplayNameGenerator)

	@property
	def creator(self):
		names = IFriendlyNamed(self._primary.creator)
		return names.alias or names.realname

	@property
	def web_root(self):
		settings = component.getUtility(IApplicationSettings)
		web_root = settings.get('web_app_root', '/NextThoughtWebApp/')
		# It MUST end with a trailing slash, but we don't want that
		return web_root[:-1]

	@property
	def href(self):
		# Default to the most stable identifier we have. If
		# we can get an actual OID, use that as it's very specific,
		# otherwise see if the object has on opinion (which may expose
		# more details than we'd like...)
		ntiid = (to_external_ntiid_oid(self._primary, mask_creator=True)
				 or getattr(self._primary, 'NTIID', None))
		if ntiid:
			# The webapp does a weird dance, like so:
			return self.request.route_url('objects.generic.traversal',
										  traverse=(),
										  _anchor="!object/ntiid/" + ntiid).replace('/dataserver2',
																					self.web_root)

		# TODO: These don't actually do what we want in terms of interacting
		# with the application...
		return self.request.resource_url(self._primary)

	def _path_to_note_container(self):
		name = self.__name__
		__traceback_info__ = name
		assert name.startswith('tag:')

		# Try to find a content unit
		# FIXME: Eww, ugly. This implementation knows entirely
		# too much. We would like to pull it out to a DisplayNameGenerator,
		# but we have nothing to really register that adapter
		# on.
		# It's also incredibly inefficient.
		lib = component.getUtility(IContentPackageLibrary)
		path = lib.pathToNTIID(name)
		if path:
			return path

		def _search(unit):
			for iface in ifaces:
				if name in iface(unit).contains_data_item_with_ntiid(name):
					return lib.pathToNTIID(unit.ntiid)
			for child in unit.children:
				r = _search(child)
				if r:
					return r

		for package in lib.contentPackages:
			r = _search(package)
			if r:
				return r

	@property
	def note_container_display_name(self):
		path = self._path_to_note_container()
		if path:
			for i in reversed(path):
				title = getattr(i, 'title', '')
				if title and title.strip():
					return title

	@property
	def note_container_href(self):
		"For note containers, we want to go to the content unit, not the note container"
		path = self._path_to_note_container()
		if path:
			ntiid = path[-1].ntiid
			parsed_ntiid = parse_ntiid(ntiid)
			# The app has another, nice, format for content
			# #!HTML/<provider>/<specific>
			provider = parsed_ntiid.provider
			specific = parsed_ntiid.specific
			return self.request.route_url('objects.generic.traversal',
										  traverse=(),
										  _anchor="!HTML/" + provider + '/' + specific).replace('/dataserver2',
																								self.web_root)


	@property
	def creator_avatar_url(self):
		return self.request.resource_url(self._primary.creator, '@@avatar')

class DigestEmailTemplateArgs(dict):

	def __init__(self):
		dict.__init__(self)
		# Yes, this creates a cycle. But
		# if someone does dict.update(self),
		# even if we override __getitem__/get,
		# __contains__, and items(), we have no guarantee
		# that the copied dict will actually return
		# our fake key
		self['context'] = self


from zope.security.interfaces import IParticipation
from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import restoreInteraction

from zope.preference.interfaces import IPreferenceGroup

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

	def historical_cap(self, delta=_ONE_WEEK):
		return self.collection_time - delta

	@property
	def is_subscribed(self):
		prefs = component.getUtility(IPreferenceGroup, name='PushNotifications.Email')
		# To get the user's
		# preference information, we must be in an interaction for that user.
		endInteraction()
		try:
			newInteraction(IParticipation(self.remoteUser))
			return prefs.email_a_summary_of_interesting_changes
		finally:
			restoreInteraction()

	def min_created_time(self, notable_data):
		last_time_collected = self.last_collected
		self.last_collected = self.collection_time

		# TODO: When should we update this? If we update it now, we risk not actually
		# sending the email. If we update it when we actually send, that turns a read
		# transaction into a write transaction. If we keep it in redis, we could reset
		# it easily enough but we need the hooks to do that...for now, we update
		# it when we collect recipients
		last_email_sent = self.last_sent
		last_viewed_data = notable_data.lastViewed or self.remoteUser.lastLoginTime
		historical_cap = self.historical_cap()

		min_created_time = max( last_email_sent, last_time_collected, last_viewed_data, historical_cap )
		return min_created_time

	def __call__(self):
		"""
		Returns a bulkemail \"recipient\" for the current user, if
		we should send a mail message.
		"""
		# If we have no email address on file, we can't send anything, obviously
		addr = IEmailAddressable(self.remoteUser,None)
		if not addr or not addr.email:
			return

		# If the user is unsubscribed, we can't send anything.
		if not self.is_subscribed:
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

		min_created_time = self.min_created_time(notable_data)
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

		logger.debug("User %s/%s had %d notable items since %s",
					  self.remoteUser, addr.email, len(sorted_by_type_time), min_created_time)
		return {'email': EmailAddresablePrincipal(self.remoteUser),
				'template_args': sorted_by_type_time,
				'since': min_created_time}


	def recipient_to_template_args(self, recipient, request):
		# Now iterate to get the actual content objects
		# (Note that grade objects are going to have a `change` content type, which is
		# unique)
		sorted_by_type_time = recipient['template_args']

		values = collections.defaultdict(list)

		notable_data = component.getMultiAdapter( (self.remoteUser, self.request),
												  IUserNotableData)

		total_found = 0
		for o in notable_data.iter_notable_intids(sorted_by_type_time, ignore_missing=True):
			total_found += 1
			classifier = component.queryAdapter(o, INotableDataEmailClassifier)
			try:
				classification = classifier.classify(o)
			except AttributeError:
				classification = None

			if classification:
				values[classification].append(o)
			else:
				total_found -= 1
				values['other'].append(o)

		# These were initially sorted by time within their own mime types,
		# but some things may have multiple mime types under the same classification,
		# so we need to resort
		result = DigestEmailTemplateArgs()
		for name, objs in values.items():
			if objs:
				objs.sort(reverse=True, key=lambda x: getattr(x, 'createdTime', 0))
				result[name] = _TemplateArgs(objs, request)

		# If we really wanted to, we could stick a user authentication token
		# on this view, but it's a lot safer not to.
		result['unsubscribe_link'] = request.resource_url(self.remoteUser, '@@unsubscribe_digest_email')
		result['email_to'] = '%s (%s)' % (recipient['email'].email, recipient['email'].id)
		result['total_found'] = total_found
		# We may want to exclude 'circled' and others from this count
		result['total_remaining'] = sum( [ x.remaining for x in result.values() if isinstance( x, _TemplateArgs ) ] )
		return result

from nti.externalization.singleton import SingletonDecorator
from .interfaces import INotableDataEmailClassifier

@interface.implementer(INotableDataEmailClassifier)
class _AbstractClassifier(object):
	__metaclass__ = SingletonDecorator

	classification = None

	def classify(self, obj):
		return self.classification

AbstractClassifier = _AbstractClassifier

@component.adapter(INote)
class _NoteClassifier(_AbstractClassifier):
	classification = 'note'

@component.adapter(ICommentPost)
class _CommentClassifier(_AbstractClassifier):

	def classify(self, obj):
		# Either this is a reply to us or this is a top-level comment in a thought or discussion.
		if ICommentPost.providedBy(obj.__parent__):
			return 'comment'

		return 'top_level_comment'

@component.adapter(IPersonalBlogEntry)
class _BlogEntryClassifier(_AbstractClassifier):
	classification = 'blog'

@component.adapter(IPersonalBlogEntryPost)
class _BlogEntryPostClassifier(_AbstractClassifier):
	classification = 'blog'

@component.adapter(ITopic)
class _TopicClassifier(_AbstractClassifier):
	classification = 'discussion'

@component.adapter(IStreamChangeEvent)
class _StreamChangeEventDispatcher(_AbstractClassifier):

	def classify(self, obj):
		# What we should do is look for a named adapter based on the
		# type of the contained object and the change type name
		# but right now we don't, hardcoding knowledge of the
		# supported types
		if obj.type == 'Circled':
			return 'circled'
		return 'grade'

class _FeedbackClassifier(_AbstractClassifier):
	classification = 'feedback'


from nti.dataserver.interfaces import IDataserver
from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate
from zope.publisher.interfaces.browser import IBrowserRequest
from nti.dataserver.interfaces import IAuthenticationPolicy
from nti.dataserver.interfaces import IImpersonatedAuthenticationPolicy
from nti.appserver.policies.site_policies import find_site_policy
from nti.appserver.policies.site_policies import guess_site_display_name

from nti.dataserver.users import Entity
from nti.dataserver.users import User
import datetime
from zope.i18n import translate
from nameparser import HumanName

@interface.implementer(IBulkEmailProcessDelegate)
class DigestEmailProcessDelegate(AbstractBulkEmailProcessDelegate):

	_subject = "Your ${site_name} Updates"

	text_template_extension = ".mak"
	template_name = 'nti.app.pushnotifications:templates/digest_email'

	@Lazy
	def _dataserver(self):
		return component.getUtility(IDataserver)

	def _accept_user(self, user):
		return IUser.providedBy(user)

	def _collector_for_user(self, user, factory=DigestEmailCollector):
		collector = factory(user, self.request)
		return collector

	def collect_recipients(self):
		# We are in an outer request, but we need to get the
		# notable data for different users. In some cases
		# this depends on the authentication policy to get
		# principal IDs, not the passed-in remote user
		# (Which is weird, I know), so we must be sure
		# to impersonate each user as we ask for notable data
		auth_policy = component.getUtility( IAuthenticationPolicy )
		imp_policy = IImpersonatedAuthenticationPolicy( auth_policy )

		# If we can find a community for the current site, we
		# must filter users to only those within that community.
		# See ICommunitySitePolicyUserEventListener
		users_folder = self._dataserver.users_folder.values()

		site_policy, _ = find_site_policy(self.request)
		com_username = getattr(site_policy, 'COM_USERNAME', None)

		comm = None
		if com_username:
			comm = Entity.get_entity(com_username)
		if comm is not None:
			# We can simply iterate it
			users_folder = comm.iter_members()

		now = time.time()
		for user in users_folder:
			if self._accept_user(user):
				imp_user = imp_policy.impersonating_userid( user.username )
				with imp_user():
					collector = self._collector_for_user(user)
					collector.collection_time = now
					possible_recipient = collector()
					if possible_recipient:
						collector.last_sent = time.time()
						possible_recipient['realname'] = IFriendlyNamed(user).realname
						yield possible_recipient

	def compute_template_args_for_recipient(self, recipient):
		user = User.get_user( recipient['email'].id, self._dataserver )
		# XXX If the user disappears, we're screwed.
		collector = DigestEmailCollector(user, self.request)

		result = collector.recipient_to_template_args(recipient, self.request)
		if not result['total_found']:
			return None

		# FIXME: This isn't right, we actually want the /user's/ locale,
		# but we don't have that stored anywhere
		locale = IBrowserRequest(self.request).locale
		dates = locale.dates
		formatter = dates.getFormatter('dateTime', length='short')
		since = recipient['since'] or 0
		when = datetime.datetime.fromtimestamp(since)

		result['site_name'] = guess_site_display_name(self.request)
		result['since_when'] = formatter.format(when)
		result['first_name'] = HumanName(recipient['realname']).first if recipient['realname'] else recipient['email'].id

		# Hmm, maybe?
		result['view'] = self
		return result


	def compute_subject_for_recipient(self, recipient):

		subject = _(self._subject,
					mapping={
							 'site_name': guess_site_display_name(self.request),
							 })
		return translate(subject, context=self.request)


class DigestEmailProcessTestingDelegate(DigestEmailProcessDelegate):

	_subject =  'TEST - ' + DigestEmailProcessDelegate._subject

	def _accept_user(self, user):
		if super(DigestEmailProcessTestingDelegate,self)._accept_user(user):
			if user.username in ('ossmkitty', 'madd2844'):
				return True

			email = getattr(IEmailAddressable(user, None), 'email', None)
			if email:
				if email.endswith('@nextthought.com'):
					return True
				if email == 'jamadden@ou.edu':
					return True

	class _Collector(DigestEmailCollector):
		no_created_cap = False
		def min_created_time(self, notable_data):
			return None if self.no_created_cap else DigestEmailCollector.min_created_time(self, notable_data)

	def _collector_for_user(self, user, factory=_Collector):
		collector = DigestEmailProcessDelegate._collector_for_user(self, user, factory=self._Collector)
		collector.no_created_cap = self.request.get('no_created_cap')
		if collector.no_created_cap:
			collector.last_collected = collector.last_sent = 0
		return collector

	def collect_recipients(self):
		for possible_recipient in super(DigestEmailProcessTestingDelegate,self).collect_recipients():
			# Reset the sent and collected times if desired
			self._collector_for_user(User.get_user(possible_recipient['email'].id, self._dataserver))

			logger.info( "User %s/%s had %d notable objects",
						 possible_recipient['email'].id, possible_recipient['email'].email,
						 len(possible_recipient['template_args']))
			if self.request.get('override_to'):
				possible_recipient['email'].email = self.request.get('override_to')
			yield possible_recipient

class DigestEmailNotableViewletBase(object):
	"""
	Base class for viewlets based on a notable object
	(an instance of this modules :class:`_TemplateArgs`).

	It is conditionally available if the template argument
	corresponding to its name is populated in the context dictionary
	(so the name attribute of the viewlet registration must match
	how we create the context dictionary).

	You can define a weight attribute in the viewlet registration as
	well to influence the order of viewlets. By default they are
	unordered.
	"""

	context = None
	__name__ = None

	@property
	def notable(self):
		return self.context.get(self.__name__)

	@property
	def available(self):
		args = self.context.get(self.__name__)
		if args:
			return True
		return False
