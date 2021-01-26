#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies and components that are related to the dynamic site of the request. Because the dataserver
itself may actually be a single domain, the HTTP `Origin <http://tools.ietf.org/html/rfc6454>`_ header is first
checked before the site. These policies are by nature tied to the existence
of a request.

TODO: This should be refactored into a package (at least). When doing so, be very careful
to preserve the names of existing persistent classes as well as the annotation factory keys.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division

logger = __import__('logging').getLogger(__name__)

import datetime
from six.moves import urllib_parse

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

from zope.component.hooks import getSite

from zope.component.interfaces import IComponents

from zope.interface.common.idatetime import IDate

from zope.dottedname import resolve as dottedname

from zope.event import notify

from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from zope.schema.fieldproperty import createFieldProperties

from zope.schema import interfaces as sch_interfaces

from zope.security.interfaces import IPrincipal

from ZODB.loglevels import TRACE

from pyramid.path import package_of
from pyramid.threadlocal import get_current_request

from nti.app.users.utils import generate_verification_email_url

from nti.appserver import MessageFactory as _

from nti.appserver.interfaces import IUserAccountRecoveryUtility
from nti.appserver.interfaces import IUserLogonEvent
from nti.appserver.interfaces import IUserCapabilityFilter
from nti.appserver.interfaces import IUserCreatedWithRequestEvent
from nti.appserver.interfaces import IUserCreatedByAdminWithRequestEvent

from nti.appserver.interfaces import UserUpgradedEvent

from nti.appserver.policies import PLACEHOLDER_USERNAME

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener
from nti.appserver.policies.interfaces import INoAccountCreationEmail
from nti.appserver.policies.interfaces import IRequireSetPassword
from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.common.emoji import has_emoji_chars

from nti.common.nameparser import human_name as np_human_name

from nti.contentfragments import censor

from nti.contentfragments.interfaces import ICensoredContentPolicy

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUser
from nti.dataserver.interfaces import INewUserPlacer
from nti.dataserver.interfaces import username_is_reserved
from nti.dataserver.interfaces import ICoppaUserWithAgreement
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement
from nti.dataserver.interfaces import ICoppaUserWithAgreementUpgraded

from nti.dataserver.shards import AbstractShardPlacer

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IEmailAddressable
from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import BlankHumanNameError
from nti.dataserver.users.interfaces import IImmutableFriendlyNamed
from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent
from nti.dataserver.users.interfaces import IWillUpdateNewEntityEvent
from nti.dataserver.users.interfaces import UsernameContainsIllegalChar

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import IExternalObjectDecorator

from nti.externalization.singleton import Singleton

from nti.mailer.interfaces import ITemplatedMailer

from nti.schema.interfaces import InvalidValue
from nti.schema.interfaces import find_most_derived_interface

from nti.site.interfaces import ITransactionSiteNames

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Code should not access this directly; move your tests to the mathcounts site package."
	" The only valid use is existing ZODB objects",
	"nti.app.sites.mathcounts.interfaces",
	"IMathcountsUser",
	"IMathcountsCoppaUserWithoutAgreement",
	"IMathcountsCoppaUserWithAgreement",
	"IMathcountsCoppaUserWithAgreementUpgraded",
	"IMathcountsCoppaUserWithoutAgreementUserProfile",
	"IMathcountsCoppaUserWithAgreementUserProfile")

def get_possible_site_names(request=None, include_default=False):
	"""
	Look for the current request, and return an ordered list
	of site names the request could be considered to be for.
	The list is ordered in preference from most specific to least
	specific. The HTTP origin is considered the most preferred, followed
	by the HTTP Host.

	:keyword bool include_default: If set to ``True`` (not the default)
		then a site named '' (the empty string) is returned as the last
		site in the iterable, making it suitable for use as an ordered
		list of adapter names.

	:return: An ordered sequence of string site names. If there is no request
		or a preferred site cannot be found, returns an empty sequence.
	"""

	request = request or get_current_request()
	if not request:  # pragma: no cover
		return () if not include_default else ('',)
	__traceback_info__ = request

	# The site tween modifies the request to have this property,
	# and our test cases do so as well, even those that don't go through the tweens
	# (There have been some unexplained cases of an AttributeError here, though?)
	site_names = getattr(request, 'possible_site_names', ())
	if include_default:
		site_names += ('',)
	return site_names

@interface.implementer(ITransactionSiteNames)
class _TransactionSiteNames(object):

	def __call__(self, *args, **kwargs):
		return get_possible_site_names(*args, **kwargs)

def _find_site_components(request, include_default=False, site_names=None):
	site_names = site_names or get_possible_site_names(request=request,
													   include_default=include_default)
	for site_name in site_names:
		if not site_name:
			components = component
		else:
			components = component.queryUtility(IComponents, name=site_name)

		if components is not None:
			return components

_marker = object()

def queryUtilityInSite(iface, request=None, site_names=None, default=None,
					   name='', return_site_name=False):
	result = _marker
	components = _find_site_components(request, include_default=True, site_names=site_names)
	if components is not None:
		result = components.queryUtility(iface, default=_marker, name=name)

	result = result if result is not _marker else default
	if not return_site_name:
		return result

	site_name = None
	if components is not None:
		site_name = components.__name__ if components.__name__ != component.__name__ else ''
	return result, site_name

def queryAdapterInSite(obj, target, request=None, site_names=None, default=None):
	"""
	Queries for named adapters following the site names, all the way up until the default
	site name.

	:keyword request: The current request to investigate for site names.
		If not given, the threadlocal request will be used.
	:keyword site_names: If given and non-empty, the list of site names to use.
		Overrides the `request` parameter.
	"""

	# This is now beginning to use z3c.baseregistry, but more needs to be done.
	components = _find_site_components(request, include_default=True, site_names=site_names)
	if components is not None:
		result = components.queryAdapter(obj, target, default=_marker)
		if result is not _marker:
			return result
	return default

def queryMultiAdapterInSite(objects, target, request=None, site_names=None, default=None):
	"""
	Queries for named adapters following the site names, all the way up until the default
	site name.

	:keyword request: The current request to investigate for site names.
		If not given, the threadlocal request will be used.
	:keyword site_names: If given and non-empty, the list of site names to use.
		Overrides the `request` parameter.

	"""
	components = _find_site_components(request, include_default=True, site_names=site_names)
	if components is not None:
		result = components.queryMultiAdapter(objects, target, default=_marker)
		if result is not _marker:
			return result
	return default

@interface.implementer(INewUserPlacer)
class RequestAwareUserPlacer(AbstractShardPlacer):
	"""
	A user placer that takes the current request's origin and host (if there is one)
	into account.

	The policy defined by this object is currently very simple and likely to evolve.
	These are the steps we take to place a user:

	#. If there is a utility named the same as the origin/host name, then we defer to that.
	   This allows configuration to trump any decisions we would make here.
	#. If there is a shard matching the origin/host name, then the user will be placed in that
	   shard.
	#. If none of the previous conditions hold (or there is no request), then we will defer to the ``default``
	   utility.

	"""

	def placeNewUser(self, user, users_directory, shards):
		placed = False
		for site_name in get_possible_site_names():
			# TODO: Convert to z3c.baseregistry components? Nothing is actually implementing
			# this at the moment.
			placer = component.queryUtility(INewUserPlacer, name=site_name)
			if placer:
				placed = True
				placer.placeNewUser(user, users_directory, shards)
			elif site_name in shards:
				placed = self.place_user_in_shard_named(user, users_directory, site_name)

			if placed:
				break

		if not placed:
			component.getUtility(INewUserPlacer, name='default').placeNewUser(user, users_directory, shards)

####
# # Handling events within particular sites
#
# TODO: It's not clear what the best way is to handle this. We have a
# few options. (NOTE: This was written before the existence of z3c.baseregistry;
# using that should simplify things notably.)
#
# The simplest is that each site-aware handler re-delegates to a named
# utility based on the site names. This works because it can be
# statically configured in files that either ship with the code or
# live on the site machine(s). However, it is limited in what it can
# do since it's not really re-firing an event.
#
# A second option is to look for a ISiteManager matching the active
# sites and really re-dispatch the event into those sites (either all
# events, by adding to zope.event, or just object events by adding an
# IObjectEvent subscriber; the former would require re-registering the
# component object event dispatcher in the subsites?). Each shard we
# have is an IPossibleSite and could have an ISiteManager added to it,
# for example, when shards match site names. That preserves
# flexibility, but has the disadvantage of requiring code to do
# configuration changes. (In some ways, the ZMI would be very nice to
# have...)
#
# A third, but similar option, is to have the shard or site objects more fully
# configured, and to re-dispatch events based on the current site. Then
# listeners for each event would be registered for (object, event_type, site_type)
# and could examine the site object for details, such as additional interfaces
# to apply or communities to join. This still requires those objects exist, and possibly be
# registered somewhere and saved in the database, but avoids the confusing complexity of
# working with multiple ISiteManagers that are not in a hierarchy.
#
# Initially, we are taking the simplest approach, and even going so far
# as to put the actual policies in code (so a config change is a code release).
#
# This is starting to get out of hand, though, and the automatic delegation of a real site
# would be very nice to have. The `EventListener` is now being delegated to for all kinds
# of random things, many of which have nothing to do with events, such as
# object externalization decoration...
#
# The first part of this, incorporating z3c.baseregistry objects is done. The next
# part of that is to integrate with traversal. At some point the ISitePolicy objects die
# and become simply normal event listeners.
####

@interface.implementer(IExternalObjectDecorator)
class SiteBasedExternalObjectDecorator(Singleton):
	"""
	Something that can be registered as a subscriber to forward
	object decoration to objects that do something for a particular site.
	These object must be registered as multi-adapters for the original object
	and the active request within the correct site policy. (Note that they are not
	subscribers, they get one shot.)

	Register this object sparingly, it is expensive.
	"""

	def decorateExternalObject(self, orig_obj, ext_obj):
		request = get_current_request()
		if not request:
			return

		adapter = component.queryMultiAdapter((orig_obj, request), IExternalObjectDecorator)
		if adapter:
			adapter.decorateExternalObject(orig_obj, ext_obj)

@interface.implementer(IExternalObjectDecorator)
class LogonLinksCreationStripper(Singleton):
	"""
	Configured for sites that are not allowing account creation through the UI.
	"""

	def decorateExternalObject(self, unused_context, result):
		result['Links'] = [	link for link in result['Links']
							if link['rel'] not in ('account.create', 'account.preflight.create')]

def find_site_policy(request=None):  # deprecated
	"""
	Find a site policy that's currently active, including the default.

	:return: A two-tuple of (policy, site_name). If no policy was found
		then the first value is None and the second value is all applicable site_names found.
	"""
	request = request or get_current_request()
	components = _find_site_components(request=request, include_default=True)
	if components is not None:
		utility = components.queryUtility(ISitePolicyUserEventListener)
		if utility:
			return utility, components.__name__ if components.__name__ != component.__name__ else ''
	return None, get_possible_site_names(request=request, include_default=True)

def guess_site_display_name(request=None):
	"""
	Attempt to return the best display name for the site of the current
	or given request.

	If the site policy provides the ``DISPLAY_NAME`` attribute as a non-empty
	string, it will be returned. Otherwise, we will attempt to derive a friendly
	display name by taking the first component of the site name and performing
	some manipulations.

	If there is no active site, the hostname of the request will be returned,
	suitably prettied up.
	"""
	request = request or get_current_request()
	policy, site_name = find_site_policy(request)

	display_name = getattr(policy, 'DISPLAY_NAME', '')
	if display_name:
		display_name = display_name.strip()
		return display_name

	if policy is None:
		site_name = site_name[0] if site_name else 'Unknown'

	base_display_name = site_name or getattr(request, 'host', 'Unknown')
	# take the domain portion
	base_display_name = base_display_name.split('.', 1)[0]
	# Strip any port that may be here (typically localhost:80, in test cases)
	if ':' in base_display_name:
		base_display_name = base_display_name[:base_display_name.index(':')]
	# replace some things we use for spaces
	base_display_name = base_display_name.replace('-', ' ')
	# and title-case it
	display_name = base_display_name.title()

	return display_name

def _dispatch_to_policy(user, event, func_name):
	"""
	Returns a true value if the event was handled by some policy.
	"""
	utility, site_name = find_site_policy()
	if utility:
		logger.log(TRACE, "Site %s wants to handle user creation event %s for %s with %s",
				   site_name, func_name, user, utility)
		getattr(utility, func_name)(user, event)
		return True

	logger.log(TRACE, "No site in %s wanted to handle user event %s for %s",
			   site_name, func_name, user)

@component.adapter(IUser, IObjectCreatedEvent)
def dispatch_user_created_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_created')

@component.adapter(IUser, IWillUpdateNewEntityEvent)
def dispatch_user_will_update_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_will_update_new')

@component.adapter(IUser, IWillCreateNewEntityEvent)
def dispatch_user_will_create_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_will_create')

@component.adapter(IUser, IUserCreatedWithRequestEvent)
def dispatch_user_created_with_request_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_created_with_request')

@component.adapter(IUser, IUserCreatedByAdminWithRequestEvent)
def dispatch_user_created_by_admin_with_request_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_created_by_admin_with_request')

@component.adapter(IUser, IUserLogonEvent)
def dispatch_user_logon_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_did_logon')

def _censor_usernames(entity, unused_event=None):
	"""
	Censor the username field of the entity. Can be used as an event
	listener as well.
	"""
	# Try a named utility so it can be overridden on a site by site basis
	policy = component.queryUtility(ICensoredContentPolicy, name='username')
	policy = policy or censor.DefaultCensoredContentPolicy()

	if policy.censor(entity.username, entity) != entity.username:
		raise FieldContainsCensoredSequence(_("Username contains a censored sequence"),
											'Username', entity.username)

	names = IFriendlyNamed(entity, None)
	if names and names.alias:  # TODO: What about realname?
		if policy.censor(names.alias, entity) != names.alias:
			raise FieldContainsCensoredSequence(_("Alias contains a censored sequence"),
												'alias', names.alias)

def _is_x_or_more_years_ago(birthdate, years_ago=13):
	if birthdate is None:
		return False

	today = datetime.date.today()
	try:
		x_years_ago = today.replace(year=today.year - years_ago)
	except ValueError:
		# Leap year
		x_years_ago = today.replace(year=today.year - years_ago,
									month=today.month + 1,
									day=1)
	return birthdate < x_years_ago

_is_thirteen_or_more_years_ago = _is_x_or_more_years_ago

def _to_date(string, field=None):
	try:
		return IDate(string) if string else None
	except InvalidValue:
		return None

# Validation errors. The class names will be used as codes,
# which will help the UI if they don't want to use our error
# messages
class BirthdateInFuture(InvalidValue): pass
class BirthdateTooRecent(InvalidValue): pass
class BirthdateTooAncient(InvalidValue): pass
class InvalidUsernamePattern(InvalidValue): pass
class UsernameMustEqualEmail(InvalidValue): pass
class UsernameCannotContainRealname(InvalidValue): pass
class FieldContainsCensoredSequence(InvalidValue): pass
class UsernameCannotContainNextthoughtCom(InvalidValue): pass
class UsernameCannotContainAt(UsernameContainsIllegalChar): pass

class MissingFirstName(sch_interfaces.RequiredMissing):
	field = 'realname'

class MissingLastName(sch_interfaces.RequiredMissing):
	field = 'realname'

class AtInUsernameImpliesMatchingEmail(InvalidValue): pass

@interface.implementer(ICommunitySitePolicyUserEventListener)
class AbstractSitePolicyEventListener(object):
	"""
	Basics of a site policy.
	"""

	createFieldProperties(ICommunitySitePolicyUserEventListener)
	_v_my_package = None

	def __find_my_package(self):
		specific_package = getattr(self, 'PACKAGE', None)
		if specific_package is not None:
			return specific_package

		if self._v_my_package is None:
			package = package_of(dottedname.resolve(type(self).__module__))
			# As a temporary measure, if we find that we are in the old
			# nti.appserver.policies package, use the nti.appserver package
			# instead. This is because the generic templates live there,
			# and it's not worth moving them until the general reorganization
			# is complete
			if package is package_of(dottedname.resolve(__name__)):
				package = dottedname.resolve('nti.appserver')
			self._v_my_package = package

		return self._v_my_package

	def _send_email_on_new_account(self, user, event):
		"""
		For new accounts where we have an email (and of course the request), we send a welcome message.

		Notice that we do not have an email collected for the ICoppaUserWithoutAgreement, so
		they will never get a notice here. (And we don't have to specifically check for that).

		Uses the self/class attribute ``NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME`` to generate the email text.
		Uses the self/class attribute ``NEW_USER_CREATED_EMAIL_SUBJECT`` to generate the subject
		"""

		self._send_new_account_email(user,
									 event,
									 self.NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME,
									 self.NEW_USER_CREATED_EMAIL_SUBJECT)

	def _send_email_on_admin_created_account(self, user, event):
		"""
		For accounts created by admins, which should be required to
		provide an email, send an appropriate welcome message

		Uses the self/class attribute ``NEW_USER_CREATED_BY_ADMIN_EMAIL_TEMPLATE_BASE_NAME`` to generate the email text.
		Uses the self/class attribute ``NEW_USER_CREATED_BY_ADMIN_EMAIL_SUBJECT`` to generate the subject
		"""

		if not event.request:  # pragma: no cover
			return

		username = user.username
		profile = IUserProfile(user)
		email = profile.email

		# Currently requires a `success` param passed in the request for
		# the target of the link to use for directing the user to a login
		# allowing them to set their initial password
		recovery_utility = component.getUtility(IUserAccountRecoveryUtility)
		reset_url = recovery_utility.get_password_reset_url(user, event.request)
		if not reset_url:
			logger.error("No recovery url found for username '%s' and email '%s'",
						 username, email)
			reset_url = None

		self._send_new_account_email(user,
									 event,
									 self.NEW_USER_CREATED_BY_ADMIN_EMAIL_TEMPLATE_BASE_NAME,
									 self.NEW_USER_CREATED_BY_ADMIN_EMAIL_SUBJECT,
									 extra_template_args={
										 'set_passcode_url': reset_url
									 })

	def _brand_name(self, request):
		return component.getMultiAdapter((getSite(), request),
										 IDisplayNameGenerator)()

	def _send_new_account_email(self,
								user,
								event,
								base_template,
								subject,
								extra_template_args=None):
		if not event.request:  # pragma: no cover
			return

		profile = IUserProfile(user)
		email = getattr(profile, 'email')
		if not email:
			return
		assert getattr(IEmailAddressable(profile, None), 'email', None) == email
		assert getattr(IPrincipal(profile, None), 'id', None) == user.username

		user_ext = to_external_object(user)
		informal_username = user_ext.get('NonI18NFirstName', profile.realname) or user.username

		args = {'user': user,
				'profile': profile,
				'email': email,
				'verify_href': '',
				'informal_username': informal_username,
				'support_email': self.SUPPORT_EMAIL,
				'site_name': self._brand_name(event.request),
				'context': user }

		if not profile.email_verified:
			email_verification_href, _ = generate_verification_email_url(user, request=event.request)
			args['verify_href'] = email_verification_href

		if extra_template_args:
			args.update(extra_template_args)

		# Need to send both HTML and plain text if we send HTML, because
		# many clients still do not render HTML emails well (e.g., the popup notification on iOS
		# only works with a text part)
		component.getUtility(ITemplatedMailer).queue_simple_html_text_email(
			base_template,
			subject=subject,
			bcc=self.NEW_USER_CREATED_BCC,
			recipients=[user],
			template_args=args,
			request=event.request,
			package=self.__find_my_package())

	def _set_landing_page_cookie(self, user, event):
		if self.LANDING_PAGE_NTIID:
			event.request.response.set_cookie(b'nti.landing_page',
											  value=urllib_parse.quote(self.LANDING_PAGE_NTIID))

	def _check_realname(self, user, required=True):
		# Icky. For some random reason we require everyone to provide
		# their real name, and we force the display name to be derived
		# from it.
		names = IFriendlyNamed(user)
		# nameparser 0.2.5+ no longer raises BlankHumanNameError, so we do
		if names.realname is None or not names.realname.strip():
			if required:
				raise BlankHumanNameError()
			return  # Not required

		human_name = np_human_name(names.realname)
		if not human_name.first:
			raise MissingFirstName(_("Please provide your first name."),
								   'realname',
								   names.realname)
		elif has_emoji_chars(human_name.first):
			raise FieldContainsCensoredSequence(_("First name contains a censored sequence."),
												'realname', names.realname)

		if not human_name.last:
			raise MissingLastName(_("Please provide your last name."),
								  'realname',
								  names.realname)
		elif has_emoji_chars(human_name.last):
			raise FieldContainsCensoredSequence(_("Last name contains a censored sequence."),
												'realname', names.realname)

		human_name.capitalize()
		names.realname = unicode(human_name)
		names.alias = human_name.first + ' ' + human_name.last

	def _censor_usernames(self, user):
		# Disabled by default
		pass

	def _check_age_makes_sense(self, user):
		profile = IUserProfile(user)
		birthdate = getattr(profile, 'birthdate', None)
		if birthdate:
			t, v = None, None
			if birthdate >= datetime.date.today():
				t = BirthdateInFuture
				v = _("Birthdate must be in the past.")
			elif not _is_x_or_more_years_ago(birthdate, 4):
				t = BirthdateTooRecent
				v = _("Birthdate must be at least four years ago.")
			elif _is_x_or_more_years_ago(birthdate, 150):
				t = BirthdateTooAncient
				v = _("Birthdate must be less than 150 years ago.")

			if t:
				raise t(v, 'birthdate', birthdate.isoformat(), value=birthdate)

	def map_validation_exception(self, incoming_data, exception):
		return exception

	def upgrade_user(self, user):
		pass

	def user_created_with_request(self, user, event):
		pass

	def user_created_by_admin_with_request(self, user, event):
		pass

	def user_will_update_new(self, user, event):
		pass

	def user_created(self, user, event):
		pass

	def user_did_logon(self, user, event):
		self._set_landing_page_cookie(user, event)

	def user_will_create(self, user, event):
		pass

class DevmodeSitePolicyEventListener(AbstractSitePolicyEventListener):

	def user_will_create(self, user, event):
		self._check_realname(user, required=False)
		self._check_age_makes_sense(user)

class GenericSitePolicyEventListener(AbstractSitePolicyEventListener):
	"""
	Implements a generic policy for all sites.
	"""

	def user_created_with_request(self, user, event):
		request = getattr(event, 'request', None)
		if not INoAccountCreationEmail.providedBy(request):
			self._send_email_on_new_account(user, event)

	def user_created_by_admin_with_request(self, user, event):
		if IRequireSetPassword.providedBy(user):
			self._send_email_on_admin_created_account(user, event)

	def user_will_create(self, user, event):
		"""
		This policy verifies naming restraints.
		"""
		self._censor_usernames(user)

		if username_is_reserved(user.username):
			raise UsernameCannotContainNextthoughtCom(
					_("That username is not valid. Please choose another."),
					'Username',
					user.username,
					value=user.username)

		# As of 2012-10-01, the acct creation UI has two very
		# anglocentric fields labeled distinctly 'first' and 'last'
		# name, which it concats to form the 'realname'. So this makes
		# realname and alias exactly the same. As of this same date,
		# we are also never returning the realname value to any site,
		# nor are we searching on it.
		self._check_realname(user)
		self._check_age_makes_sense(user)

class GenericKidSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements the starting policy for the sites with kids.

	.. note:: This site policy has a dependency between username and realname
		values. To disable this dependency during preflight checking,
		use exactly the placeholder objects defined in this policy.
	"""

	IF_ROOT = ICoppaUser
	IF_WITH_AGREEMENT = ICoppaUserWithAgreement
	IF_WOUT_AGREEMENT = ICoppaUserWithoutAgreement
	IF_WITH_AGREEMENT_UPGRADED = ICoppaUserWithAgreementUpgraded

	def upgrade_user(self, user):
		if not self.IF_WOUT_AGREEMENT.providedBy(user):
			logger.debug("No need to upgrade user %s that doesn't provide %s",
						 user, self.IF_WOUT_AGREEMENT)
			request = get_current_request()
			if request is not None and getattr(request, 'session', None) is not None:
				request.session.flash(
						"User %s doesn't need to be upgraded" % user, queue='warn')
			return False

		# Copy the profile info. First, adapt to the old profile:
		orig_profile = IUserProfile(user)
		# Then adjust the interfaces
		interface.noLongerProvides(user, self.IF_WOUT_AGREEMENT)
		interface.alsoProvides(user, self.IF_WITH_AGREEMENT_UPGRADED)
		# Now get the new profile
		new_profile = IUserProfile(user)
		# If they changed, adjust them, copying in any missing data
		if orig_profile is not new_profile:
			most_derived_profile_iface = find_most_derived_interface(new_profile, IUserProfile)
			for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
				if interface.interfaces.IMethod.providedBy(field):
					continue

				if getattr(orig_profile, name, None):  # Only copy things that have values. Let defaults be used otherwise
					setattr(new_profile, name, getattr(orig_profile, name))

		# user.transitionTime = time.time()

		notify(UserUpgradedEvent(user,
								 restricted_interface=self.IF_WOUT_AGREEMENT,
								 restricted_profile=orig_profile,
								 upgraded_interface=self.IF_WITH_AGREEMENT,
								 upgraded_profile=new_profile,
								 request=get_current_request()))
		return True
		# TODO: If the new profile required some values the old one didn't, then what?
		# Prime example: email, not required for kids, yes required for adults.

	def user_will_update_new(self, user, event):
		"""
		This policy applies the :class:`nti.dataserver.interfaces.ICoppaUserWithoutAgreement` or
		the :class:`nti.dataserver.interfaces.ICoppaUserWithAgreement` interface
		to the object, which drives the available data to store.
		"""

		interface.alsoProvides(user, self.IF_ROOT)
		iface_to_provide = self.IF_WOUT_AGREEMENT

		if (event.ext_value.get('birthdate')
			and _is_thirteen_or_more_years_ago(_to_date(event.ext_value['birthdate'],
														'birthdate'))):
			iface_to_provide = self.IF_WITH_AGREEMENT
		elif 'contact_email' in event.ext_value and 'email' not in event.ext_value:
			event.ext_value['email'] = event.ext_value['contact_email']

		interface.alsoProvides(user, iface_to_provide)

	def user_created(self, user, event):
		"""
		Makes the user immutably named.
		"""
		super(GenericKidSitePolicyEventListener, self).user_created(user, event)
		interface.alsoProvides(user, IImmutableFriendlyNamed)

	def user_will_create(self, user, event):
		super(GenericKidSitePolicyEventListener, self).user_will_create(user, event)
		names = IFriendlyNamed(user)
		# Force the alias to be the same as the username
		names.alias = user.username

		# Match the format of, e.g, WrongTypeError: message, field/type, value
		# the view likes this

		# We require a realname, at least the first name, it must already be given.
		# parse it now. This raises BlankHumanName if missing. This was checked by super
		human_name = np_human_name(names.realname)

		# Disable username/realname dependency checking if we are using placeholder data
		if user.username is not PLACEHOLDER_USERNAME:
			human_name_parts = human_name.first_list + human_name.middle_list + human_name.last_list
			if any((x.lower() in user.username.lower() for x in human_name_parts)):
				raise UsernameCannotContainRealname(
					_("Username ${username} cannot include any part of the real name ${realname}.",
					  mapping={'username': user.username, 'realname': names.realname}),
					'Username', user.username, value=user.username, field='Username')

		if '@' in user.username:
			raise UsernameCannotContainAt(user.username,
										  user.ALLOWED_USERNAME_CHARS).new_instance_restricting_chars('@')

		# This much is handled in the will_update_event
		# profile = user_interfaces.IUserProfile( user )
		# if profile.birthdate and _is_thirteen_or_more_years_ago( profile.birthdate ):
			# If we can show the kid is actually at least 13, then
			# we don't need to get an agreement

		if ICoppaUserWithoutAgreement.providedBy(user):
			# We can only store the first name for little kids
			names.realname = human_name.first

	def map_validation_exception(self, incoming_data, exception):
		if type(exception) == UsernameContainsIllegalChar:
			return exception.new_instance_restricting_chars('@')
		return exception

class GenericAdultSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements a generic policy for adult sites.
	"""

	def user_will_update_new(self, user, event):
		"""
		Also enforces the email requirement constraint for newly created objects.
		"""
		super(GenericAdultSitePolicyEventListener, self).user_will_update_new(user, event)
		ext_value = getattr(event, 'ext_value', {})
		if 'email' not in ext_value and '@' in ext_value.get('Username', ''):
			ext_value['email'] = ext_value['Username']

	def _check_email(self, user):
		profile = IUserProfile(user)
		if '@' in user.username:
			# If the username is not a valid email address, nothing further
			# is required.
			if checkEmailAddress(user.username):
				# If it is a valid email address, it must match the
				# email
				email = getattr(profile, 'email', None)
				if not email:
					profile.email = user.username
				elif user.username != email:
					msg = "If you want to use an email address for the username, it must match the email address you enter"
					raise AtInUsernameImpliesMatchingEmail(msg, 'Username', user.username)

	def user_will_create(self, user, event):
		"""
		This policy verifies naming restraints.
		"""
		super(GenericAdultSitePolicyEventListener, self).user_will_create(user, event)
		self._check_email(user)

# Profiles for MC

zope.deferredimport.deprecatedFrom(
	"Code should not access this directly; move your tests to the mathcounts site package."
	" The only valid use is existing ZODB objects",
	'nti.app.sites.mathcounts.profile',
	"MathcountsCoppaUserWithoutAgreementUserProfile",
	"MathcountsCoppaUserWithAgreementUserProfile")

@interface.implementer(IUserCapabilityFilter)
@component.adapter(ICoppaUserWithoutAgreement)
class NoAvatarUploadCapabilityFilter(object):
	"""
	Removes the ability to upload avatars.
	"""

	def __init__(self, context=None):
		pass

	def filterCapabilities(self, capabilities):
		result = set(capabilities)
		result.discard('nti.platform.customization.avatar_upload')
		return result

@interface.implementer(IUserCapabilityFilter)
@component.adapter(ICoppaUserWithoutAgreement)
class NoDFLCapabilityFilter(NoAvatarUploadCapabilityFilter):
	"""
	Removes the ability to create DFLs.
	"""

	def filterCapabilities(self, capabilities):
		result = super(NoDFLCapabilityFilter, self).filterCapabilities(capabilities)
		result.discard('nti.platform.p2p.dynamicfriendslists')
		return result

@interface.implementer(IUserCapabilityFilter)
@component.adapter(ICoppaUserWithoutAgreement)
class NoChatAvatarDFLCapabilityFilter(NoDFLCapabilityFilter):
	"""
	Removes chat.
	"""

	def filterCapabilities(self, capabilities):
		result = super(NoChatAvatarDFLCapabilityFilter, self).filterCapabilities(capabilities)
		result.discard('nti.platform.p2p.chat')
		return result

@interface.implementer(ICommunitySitePolicyUserEventListener)
class AdultCommunitySitePolicyEventListener(GenericAdultSitePolicyEventListener):
	"""
	Implements the policy for an adult site, adding new users to a single community.
	"""


def default_site_policy_factory(policy_factory=None,
                                brand=None,
                                display_name=None,
                                com_username=None,
                                com_alias=None,
                                com_realname=None):
	"""
	A factory that creates and initalizes a site policy. If no factory is provided a
	AdultCommunitySitePolicyEventListener or a
	GenericAdultSitePolicyEventListener is created based on whether or
	not a com_username is provided.
	"""
	if policy_factory is None:
		policy_factory = AdultCommunitySitePolicyEventListener if com_username is not None else GenericAdultSitePolicyEventListener
	policy = policy_factory()

	# brand is required but has a default
	if brand is not None:
		policy.BRAND = brand

	policy.DISPLAY_NAME = display_name

	if ICommunitySitePolicyUserEventListener.providedBy(policy) and com_username:
		policy.COM_USERNAME = com_username
		policy.COM_ALIAS = com_alias
		policy.COM_REALNAME = com_realname

	return policy

# BWC import for objects in the database
zope.deferredimport.deprecatedFrom(
	"Code should not access this directly; move your tests to the columbia site package."
	" The only valid use is existing ZODB objects",
	"nti.app.sites.columbia.interfaces",
	"IColumbiaBusinessUserProfile")

zope.deferredimport.deprecatedFrom(
	"Code should not access this directly; move your tests to the columbia site package."
	" The only valid use is existing ZODB objects",
	"nti.app.sites.columbia.profile",
	"ColumbiaBusinessUserProfile")
