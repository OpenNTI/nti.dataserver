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
import hashlib
import datetime
import nameparser
import collections

from nameparser import HumanName

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.interface.interfaces import ComponentLookupError

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IntIdMissingError

from zope.i18n import translate

from zope.publisher.interfaces.browser import IBrowserRequest

from zc.displayname.interfaces import IDisplayNameGenerator

from pyramid.traversal import find_interface

from nti.app.bulkemail.delegate import AbstractBulkEmailProcessDelegate

from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate

from nti.app.notabledata.interfaces import IUserNotableData

from nti.app.pushnotifications import email_notifications_preference

from nti.app.pushnotifications.interfaces import INotableDataEmailClassifier

from nti.app.pushnotifications.utils import generate_unsubscribe_url

from nti.app.users.utils import get_members_by_site

from nti.appserver.context_providers import get_trusted_top_level_contexts

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.policies.site_policies import find_site_policy
from nti.appserver.policies.site_policies import guess_site_display_name

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.coremetadata.interfaces import IContainerContext

from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IAuthenticationPolicy
from nti.dataserver.interfaces import IUserDigestEmailMetadata
from nti.dataserver.interfaces import IImpersonatedAuthenticationPolicy

from nti.dataserver.users.interfaces import IAvatarURL
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.users.users import User

from nti.externalization.singleton import Singleton

from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import EmailAddresablePrincipal

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

_ONE_WEEK = 7 * 24 * 60 * 60
_TWO_WEEKS = _ONE_WEEK * 2
_ONE_MONTH = _TWO_WEEKS * 2
_TWO_MONTH = _ONE_MONTH * 2

AVATAR_BG_COLORS = [ "#5E35B1","#3949AB","#1E88E5","#039BE5",
					"#00ACC1","#00897B","#43A047","#7CB342",
					"#C0CA33","#FDD835","#FFB300", "#FB8C00","#F4511E"]


class _TemplateArgs(object):
	"""
	Handles values for presentation per item.
	"""

	def __init__(self, objs, request, remoteUser=None):
		self.request = request
		self._primary = objs[0]
		self.remaining = len( objs ) - 1
		self.remoteUser = remoteUser

	def __getattr__(self, name):
		return getattr(self._primary, name)

	@Lazy
	def __parent__(self):
		return _TemplateArgs( (self._primary.__parent__,), self.request)

	@Lazy
	def assignment_name(self):
		try:
			from nti.assessment.interfaces import IQAssignment
			from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem
			item = find_interface(self._primary, IUsersCourseAssignmentHistoryItem)
			asg_id = None
			if item is not None:
				asg_id = item.assignmentId
			else:
				# We could be a grade
				asg_id = getattr(getattr(self._primary, 'object', None), 'AssignmentId', None)

			if asg_id is not None:
				asg = component.queryUtility(IQAssignment, name=asg_id)
				return getattr(asg, 'title', None)
		except ImportError:
			pass
		return None

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
	def total_remaining_href(self):
		return self.request.route_url('objects.generic.traversal',
									  'notifications',
									  traverse=()).replace('/dataserver2',
														   self.web_root)

	@property
	def href(self):
		# Default to the most stable identifier we have. If
		# we can get an actual OID, use that as it's very specific,
		# otherwise see if the object has on opinion (which may expose
		# more details than we'd like...)
		ntiid = (to_external_ntiid_oid(self._primary, mask_creator=True)
				 or getattr(self._primary, 'NTIID', None))
		if ntiid:
			# The clients do not use the prefix.
			ntiid = ntiid.replace( 'tag:nextthought.com,2011-10:', '' )
			return self.request.route_url('objects.generic.traversal',
										  'id',
										  ntiid,
										  traverse=()).replace('/dataserver2',
																self.web_root)

		# TODO: These don't actually do what we want in terms of interacting
		# with the application...
		return self.request.resource_url(self._primary)

	@property
	def creator_avatar_url(self):
		avatar_container = IAvatarURL( self._primary.creator )
		if avatar_container.avatarURL:
			return self.request.resource_url(self._primary.creator, '@@avatar')
		return None

	@property
	def creator_avatar_initials(self):
		named = IFriendlyNamed( self._primary.creator )
		human_name = None
		if named and named.realname:
			human_name = nameparser.HumanName( named.realname )
		# User's initials if we have both first and last
		if human_name and human_name.first and human_name.last:
			result = human_name.first[0] + human_name.last[0]
		# Or the first initial of alias/real/username
		else:
			named = named.alias or named.realname or self._primary.creator.username
			result = named[0]
		return result

	@property
	def creator_avatar_bg_color(self):
		# Hash the username into our BG color array.
		username = self._primary.creator.username
		username_hash = hashlib.md5( username.lower() ).hexdigest()
		username_hash = int( username_hash, 16 )
		index = username_hash % len( AVATAR_BG_COLORS )
		result = AVATAR_BG_COLORS[ index ]
		return result

class NotableGroupContext(dict):

	def __init__(self, notable_context, notable_dict, remaining=0):
		self.notable_context = notable_context
		self.context = notable_dict
		self.remaining = remaining

@component.adapter(IUser, interface.Interface)
class DigestEmailCollector(object):

	def __init__(self, context, request):
		self.remoteUser = context
		self.request = request
		self.time_metadata = IUserDigestEmailMetadata( self.remoteUser )

	last_sent = property(lambda x: x.time_metadata.last_sent,
						 lambda x, new_time: setattr( x.time_metadata, 'last_sent', new_time ))
	last_collected = property(lambda x: x.time_metadata.last_collected,
						 	  lambda x, new_time: setattr( x.time_metadata, 'last_collected', new_time ))

	@Lazy
	def collection_time(self):
		return time.time()

	def historical_cap(self, delta=_ONE_WEEK):
		return self.collection_time - delta

	@property
	def is_subscribed(self):
		with email_notifications_preference(self.remoteUser) as prefs:
			return prefs.email_a_summary_of_interesting_changes

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

		min_created_time = max(last_email_sent, last_time_collected, last_viewed_data, historical_cap)
		return min_created_time

	def __call__(self):
		"""
		Returns a bulkemail \"recipient\" for the current user, if
		we should send a mail message.
		"""
		# If we have no email address on file, we can't send anything, obviously
		addr = IEmailAddressable(self.remoteUser, None)
		if not addr or not addr.email:
			return

		# If the user is unsubscribed, we can't send anything.
		if not self.is_subscribed:
			return

		# validate that the user has not been removed
		# we saw this in janux after a user removal
		try:
			intids = component.getUtility(IIntIds)
			intids.getId(self.remoteUser)
		except ComponentLookupError:
			return
		except IntIdMissingError:
			logger.error("Ignoring removed/unregistered user %s", self.remoteUser)
			return

		notable_data = component.getMultiAdapter((self.remoteUser, self.request),
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
			logger.debug("[%s] User %s/%s had 0 notable items since %s",
						getSite().__name__,
						self.remoteUser, addr.email, min_created_time)

			return

		# We need to group them by type in order to provide group summaries,
		# but we only want to display the complete information
		# about the first (most recent) item in each group.
		# TODO: There should be heuristics around that, it should be the
		# first, most notable, thing
		# JZ 9.2016 - We used to also sort by mimetype to group objects (not sure why).
		# As a side-effect of this, items not in the mimetype index were dropped.
		# Now, we group by context.

		# So first we sort them by created time, descending.
		sorted_by_time = notable_data.sort_notable_intids(notable_intids_since_last_viewed,
														  reverse=True,
														  reify=True)

		logger.info("[%s] User %s/%s had %d notable items since %s",
					getSite().__name__,
					self.remoteUser,
					addr.email, len(sorted_by_time), min_created_time)
		return {'email': EmailAddresablePrincipal(self.remoteUser),
				'template_args': sorted_by_time,
				'since': min_created_time}

	def _get_top_level_context(self, obj):
		"""
		Get the top level context for our object.
		"""
		# Just grab the title since this is what we display. This also
		# collapses possible different catalog entries into a single
		# entry, which we want.
		result = None
		container_context = IContainerContext(obj, None)
		if container_context:
			context_id = container_context.context_id
			result = find_object_with_ntiid(context_id)
		if result is None:
			top_level_contexts = get_trusted_top_level_contexts(obj)
			result = None
			if top_level_contexts:
				top_level_contexts = tuple(top_level_contexts)
				result = top_level_contexts[0]

		result = getattr(result, 'title', 'General Activity')
		return result

	def recipient_to_template_args(self, recipient, request):
		# Now iterate to get the actual content objects
		# (Note that grade objects are going to have a `change` content type, which is
		# unique)
		sorted_by_time = recipient['template_args']
		values = collections.OrderedDict()

		notable_data = component.getMultiAdapter((self.remoteUser, self.request),
												  IUserNotableData)

		total_found = 0
		# Since we are sorted by time, our notable groups will be sorted by time as well
		# (groups with most recent events will come first).
		for o in notable_data.iter_notable_intids(sorted_by_time):
			top_level_context = self._get_top_level_context( o )
			class_dict = values.setdefault( top_level_context, collections.defaultdict( list ) )

			total_found += 1
			classifier = component.queryAdapter(o, INotableDataEmailClassifier)
			try:
				classification = classifier.classify(o)
			except AttributeError:
				classification = None

			if classification:
				class_dict[classification].append(o)
			else:
				total_found -= 1
				class_dict['other'].append(o)

		# Now gather our objects for display.
		result = {}
		result['notable_groups'] = notable_groups = []
		total_remaining = 0
		for top_level_context, class_dict in values.items():
			new_class_dict = {}
			obj_count = 0
			for class_name, objs in class_dict.items() or {}:
				obj_count += len( objs )
				# We used to sort our objects here by created time. Should no longer
				# be necessary.

				# This isn't quite what we want (?), we're limiting ourselves to
				# displaying one object per type (without more work).
				new_class_dict[ class_name ] = _TemplateArgs( objs, request, self.remoteUser )
			# We display one per type; whatever left is our remaining per group.
			remaining = obj_count - len( new_class_dict )
			total_remaining += remaining
			notable_groups.append( NotableGroupContext( top_level_context, new_class_dict, remaining ))

		result['unsubscribe_link'] = generate_unsubscribe_url(self.remoteUser, request)
		result['email_to'] = '%s (%s)' % (recipient['email'].email, recipient['email'].id)
		result['total_found'] = total_found
		result['total_remaining'] = total_remaining
		if result['total_remaining']:
			result['total_remaining_href'] = _TemplateArgs( (None,), request, self.remoteUser ).total_remaining_href
		return result

@interface.implementer(INotableDataEmailClassifier)
class _AbstractClassifier(Singleton):

	classification = None

	def classify(self, unused_obj):
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

	def get_process_site(self):
		policy, site_or_sites = find_site_policy(self.request)
		if policy is not None:
			# we found a site (may be empty)
			result = site_or_sites
		else:
			result = site_or_sites[0] if site_or_sites else None
		# check against current site
		result = result or getattr(getSite(), '__name__', None)
		return result

	def get_process_site_users(self):
		site_name = self.get_process_site()
		if site_name:
			return get_members_by_site(site_name)

	def _display_name(self, user):
		return component.getMultiAdapter((user, self.request), IDisplayNameGenerator)()

	def collect_recipients(self):
		# We are in an outer request, but we need to get the
		# notable data for different users. In some cases
		# this depends on the authentication policy to get
		# principal IDs, not the passed-in remote user
		# (Which is weird, I know), so we must be sure
		# to impersonate each user as we ask for notable data
		auth_policy = component.getUtility(IAuthenticationPolicy)
		imp_policy = IImpersonatedAuthenticationPolicy(auth_policy)

		now = time.time()
		for user in self.get_process_site_users() or ():
			if self._accept_user(user):
				# pylint: disable=too-many-function-args
				imp_user = imp_policy.impersonating_userid(user.username)
				with imp_user():
					collector = self._collector_for_user(user)
					collector.collection_time = now
					possible_recipient = collector()
					if possible_recipient:
						collector.last_sent = time.time()
						possible_recipient['display_name'] = self._display_name(user)
						yield possible_recipient

	def compute_template_args_for_recipient(self, recipient):
		user = User.get_user(recipient['email'].id, self._dataserver)
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
		result['display_name'] = recipient['display_name']

		# Hmm, maybe?
		result['view'] = self
		return result

	def compute_subject_for_recipient(self, unused_recipient):
		"""
		Prefer the site brand first, then falling back to a site display name.
		"""
		policy = component.getUtility(ISitePolicyUserEventListener)
		display_name = getattr(policy, 'BRAND', '')
		if display_name:
			display_name = display_name.strip()
		else:
			display_name = guess_site_display_name(self.request)

		subject = _(self._subject,
					mapping={
							 'site_name': display_name,
							 })
		return translate(subject, context=self.request)

class DigestEmailProcessTestingDelegate(DigestEmailProcessDelegate):

	_subject = 'TEST - ' + DigestEmailProcessDelegate._subject

	def _accept_user(self, user):
		if super(DigestEmailProcessTestingDelegate, self)._accept_user(user):
			if user.username in ('ossmkitty', 'madd2844'):
				return True

			email = getattr(IEmailAddressable(user, None), 'email', None)
			if email:
				if 	   email == 'jamadden@ou.edu' \
					or email == 'jzuech3@gmail.com' \
					or email == 'ntiqatesting@gmail.com' \
					or email.endswith('@nextthought.com'):
					return True

	class _Collector(DigestEmailCollector):
		no_created_cap = False
		def min_created_time(self, notable_data):
			return None if self.no_created_cap else DigestEmailCollector.min_created_time(self, notable_data)

	def _collector_for_user(self, user, unused_factory=_Collector):
		collector = DigestEmailProcessDelegate._collector_for_user(self, user, self._Collector)
		collector.no_created_cap = self.request.get('no_created_cap')
		if collector.no_created_cap:
			collector.last_collected = collector.last_sent = 0
		return collector

	def collect_recipients(self):
		for possible_recipient in super(DigestEmailProcessTestingDelegate, self).collect_recipients():
			# Reset the sent and collected times if desired
			self._collector_for_user(User.get_user(possible_recipient['email'].id, self._dataserver))

			logger.info("User %s/%s had %d notable objects",
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
