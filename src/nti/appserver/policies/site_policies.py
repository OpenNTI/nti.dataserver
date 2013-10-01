#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies and components that are related to the dynamic site of the request. Because the dataserver
itself may actually be a single domain, the HTTP `Origin <http://tools.ietf.org/html/rfc6454>`_ header is first
checked before the site. These policies are by nature tied to the existence
of a request.

TODO: This should be refactored into a package (at least). When doing so, be very careful
to preserve the names of existing persistent classes as well as the annotation factory keys.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import urllib
import datetime
import nameparser

from nti.appserver import MessageFactory as _

import zope.annotation
from zope import component
from zope import interface
from zope.event import notify
from zope.interface.common.idatetime import IDate
from zope.component.interfaces import IComponents
from zope.schema import interfaces as sch_interfaces
from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.dottedname import resolve as dottedname

from ZODB.loglevels import TRACE

from pyramid.threadlocal import get_current_request
from pyramid.path import package_of

from nti.appserver import interfaces as app_interfaces
from nti.appserver._email_utils import queue_simple_html_text_email

from nti.contentfragments import censor

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import users
from nti.dataserver.users import user_profile
from nti.dataserver import shards as nti_shards
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization import interfaces as ext_interfaces

from nti.externalization.singleton import SingletonDecorator

from nti.utils.schema import InvalidValue
from nti.utils.schema import find_most_derived_interface

from . import sites
from .interfaces import IMathcountsUser
from .interfaces import ISitePolicyUserEventListener
from .interfaces import IColumbiaBusinessUserProfile
from .interfaces import IMathcountsCoppaUserWithAgreement
from .interfaces import IMathcountsCoppaUserWithoutAgreement
from .interfaces import IMathcountsCoppaUserWithAgreementUpgraded
from .interfaces import IMathcountsCoppaUserWithAgreementUserProfile
from .interfaces import IMathcountsCoppaUserWithoutAgreementUserProfile

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
	site_names = request.possible_site_names

	if include_default:
		site_names += ('',)
	return site_names

def _find_site_components(request, include_default=False, site_names=None):
	site_names = site_names or get_possible_site_names(request=request, include_default=include_default)
	for site_name in site_names:
		if not site_name:
			components = component
		else:
			components = component.queryUtility(IComponents, name=site_name)

		if components is not None:
			return components

_marker = object()

def queryUtilityInSite(iface, request=None, site_names=None, default=None, name='', return_site_name=False):
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


@component.adapter(lib_interfaces.IS3Key)
@interface.implementer(lib_interfaces.IAbsoluteContentUnitHrefMapper)
class RequestAwareS3KeyHrefMapper(object):
	"""
	Produces HTTP URLs for keys in buckets.	Takes steps to work with CORS
	and other distribution strategies.

	Use this mapper when the bucket name is a DNS name, and the bucket name
	also has a DNS CNAME set up for it, and the application accessing the content
	was served from the same CNAME origin (or doesn't care about cross-origin concerns).
	"""
	href = None

	def __init__(self, key):
		# TODO: The following may not be the case?
		# We have to force HTTP here, because using https (or protocol relative)
		# falls down for the browser: the certs on the CNAME we redirect to, *.s3.aws.amazon.com
		# don't match for bucket.name host
		sites = get_possible_site_names()
		if sites:
			# In the CORS case, we may be coming from an origin, to the dataserver
			# and serving content which ought to come back from the origin CDN. We cannot use
			# the request.host (Host) header, because that would name the dataserver, which
			# might not be the content origin. The preferred sites send back the
			# origin first
			self.href = 'http://' + sites[0] + '/' + key.key
		else:
			self.href = 'http://' + key.bucket.name + '/' + key.key


@interface.implementer(nti_interfaces.INewUserPlacer)
class RequestAwareUserPlacer(nti_shards.AbstractShardPlacer):
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
			placer = component.queryUtility(nti_interfaces.INewUserPlacer, name=site_name)
			if placer:
				placed = True
				placer.placeNewUser(user, users_directory, shards)
			elif site_name in shards:
				placed = self.place_user_in_shard_named(user, users_directory, site_name)

			if placed:
				break

		if not placed:
			component.getUtility(nti_interfaces.INewUserPlacer, name='default').placeNewUser(user, users_directory, shards)


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

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class SiteBasedExternalObjectDecorator(object):
	"""
	Something that can be registered as a subscriber to forward
	object decoration to objects that do something for a particular site.
	These object must be registered as multi-adapters for the original object
	and the active request within the correct site policy. (Note that they are not
	subscribers, they get one shot.)

	Register this object sparingly, it is expensive.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, orig_obj, ext_obj):
		request = get_current_request()
		if not request:
			return

		adapter = component.queryMultiAdapter((orig_obj, request), ext_interfaces.IExternalObjectDecorator)
		if adapter:
			adapter.decorateExternalObject(orig_obj, ext_obj)


@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class LogonLinksCreationStripper(object):
	"""
	Configured for sites that are not allowing account creation through the UI.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, orig_obj, result):
		result['Links'] = [link for link in result['Links'] if link['rel'] not in ('account.create', 'account.preflight.create')]


def find_site_policy(request=None):  # deprecated
	"""
	Find a site policy that's currently active, including the default.

	:return: A two-tuple of (policy, site_name). If no policy was found
		then the first value is None and the second value is all applicable site_names found.
	"""
	components = _find_site_components(request=request, include_default=True)
	if components is not None:
		utility = components.queryUtility(ISitePolicyUserEventListener)
		if utility:
			return utility, components.__name__ if components.__name__ != component.__name__ else ''
	return None, get_possible_site_names(request=request, include_default=True)

def _dispatch_to_policy(user, event, func_name):
	"""
	Returns a true value if the event was handled by some policy.
	"""
	utility, site_name = find_site_policy()
	if utility:
		logger.log(TRACE, "Site %s wants to handle user creation event %s for %s with %s", site_name, func_name, user, utility)
		getattr(utility, func_name)(user, event)
		return True

	logger.log(TRACE, "No site in %s wanted to handle user event %s for %s", site_name, func_name, user)


@component.adapter(nti_interfaces.IUser, IObjectCreatedEvent)
def dispatch_user_created_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_created')

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillUpdateNewEntityEvent)
def dispatch_user_will_update_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_will_update_new')

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillCreateNewEntityEvent)
def dispatch_user_will_create_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_will_create')

@component.adapter(nti_interfaces.IUser, app_interfaces.IUserCreatedWithRequestEvent)
def dispatch_user_created_with_request_to_site_policy(user, event):
	_dispatch_to_policy(user, event, 'user_created_with_request')

@component.adapter(nti_interfaces.IUser, app_interfaces.IUserLogonEvent)
def dispatch_user_logon_to_site_policy(user, event):
	_dispatch_to_policy( user, event, 'user_did_logon' )

def _censor_usernames(entity, event=None):
	"""
	Censore the username field of the entity. Can be used as an event listener as well.
	"""
	policy = censor.DefaultCensoredContentPolicy()

	if policy.censor(entity.username, entity) != entity.username:
		raise FieldContainsCensoredSequence(_("Username contains a censored sequence"), 'Username', entity.username)

	names = user_interfaces.IFriendlyNamed(entity, None)
	if names and names.alias:  # TODO: What about realname?
		if policy.censor(names.alias, entity) != names.alias:
			raise FieldContainsCensoredSequence(_("Alias contains a censored sequence"), 'alias', names.alias)

def _is_x_or_more_years_ago(birthdate, years_ago=13):

	today = datetime.date.today()
	x_years_ago = datetime.date.today().replace(year=today.year - years_ago)

	return birthdate < x_years_ago

_is_thirteen_or_more_years_ago = _is_x_or_more_years_ago

# Validation errors. The class names will be used as codes,
# which will help the UI if they don't want to use our error
# messages
class BirthdateInFuture(InvalidValue): pass
class BirthdateTooRecent(InvalidValue): pass
class BirthdateTooAncient(InvalidValue): pass
class InvalidUsernamePattern(InvalidValue): pass
class UsernameCannotContainRealname(InvalidValue): pass
class FieldContainsCensoredSequence(InvalidValue): pass
class UsernameCannotContainNextthoughtCom(InvalidValue): pass
class UsernameCannotContainAt(user_interfaces.UsernameContainsIllegalChar): pass

class MissingFirstName(sch_interfaces.RequiredMissing):
	field = 'realname'

class MissingLastName(sch_interfaces.RequiredMissing):
	field = 'realname'

class AtInUsernameImpliesMatchingEmail(InvalidValue): pass

@interface.implementer(ISitePolicyUserEventListener)
class GenericSitePolicyEventListener(object):
	"""
	Implements a generic policy for all sites.
	"""

	#: The asset spec for a template having both text and
	#: HTML versions. If the asset spec is a bare name
	#: like "foobar", it is assumed to be located in the
	#: ``templates`` directory in the package this object
	#: is located in. Otherwise, it can be a complete spec
	#: such as "the.package:other_dir/foobar"
	NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = 'new_user_created'
	NEW_USER_CREATED_EMAIL_SUBJECT = _("Welcome to NextThought")

	#: If defined, this will be send in the ``nti.landing_page``
	#: cookie when a user logs on. Must be a byte string.
	LANDING_PAGE_NTIID = None

	_v_my_package = None

	def user_created_with_request(self, user, event):
		self._send_email_on_new_account(user, event)

	def _join_community_user_created(self, user, event):
		"""
		Helper method that places newly created users in the community defined by the fields
		of this object (creating it if it doesn't exist).
		"""
		if self.COM_USERNAME and self.COM_ALIAS and self.COM_REALNAME:
			community = users.Entity.get_entity(self.COM_USERNAME)
			if community is None:
				community = users.Community.create_community(username=self.COM_USERNAME)
				com_names = user_interfaces.IFriendlyNamed(community)
				com_names.alias = self.COM_ALIAS
				com_names.realname = self.COM_REALNAME

			user.record_dynamic_membership(community)
			user.follow(community)

	def __find_my_package(self):
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

		if not event.request:  # pragma: no cover
			return

		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email')
		if not email:
			return

		# Need to send both HTML and plain text if we send HTML, because
		# many clients still do not render HTML emails well (e.g., the popup notification on iOS
		# only works with a text part)
		queue_simple_html_text_email(self.NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME,
									 subject=self.NEW_USER_CREATED_EMAIL_SUBJECT,
									 recipients=[email],
									 template_args={'user': user, 'profile': profile, 'context': user },
									 request=event.request,
									 package=self.__find_my_package())

	def map_validation_exception(self, incoming_data, exception):
		return exception

	def upgrade_user(self, user):
		pass

	def user_will_update_new(self, user, event):
		pass

	def user_created(self, user, event):
		pass

	def user_did_logon(self, user, event):
		self._set_landing_page_cookie(user, event)

	def _set_landing_page_cookie( self, user, event ):
		if self.LANDING_PAGE_NTIID:
			event.request.response.set_cookie(b'nti.landing_page',
											   value=urllib.quote(self.LANDING_PAGE_NTIID) )

	def _check_name(self, user):
		# Icky. For some random reason we require everyone to provide their real name,
		# and we force the display name to be derived from it.
		names = user_interfaces.IFriendlyNamed(user)
		# nameparser 0.2.5 no longer raises BlankHumanNameError, so we do
		if names.realname is None or not names.realname.strip():
			raise nameparser.parser.BlankHumanNameError()
		human_name = nameparser.HumanName(names.realname)
		if not human_name.first:
			raise MissingFirstName(_("Please provide your first name."), 'realname', names.realname)
		if not human_name.last:
			raise MissingLastName(_("Please provide your last name."), 'realname', names.realname)
		human_name.capitalize()
		names.realname = unicode(human_name)
		names.alias = human_name.first + ' ' + human_name.last

	def _censor_usernames(self, user):
		_censor_usernames(user)

	def user_will_create(self, user, event):
		"""
		This policy verifies naming restraints.
		"""
		self._censor_usernames(user)

		if user.username.endswith('@nextthought.com') or nti_interfaces.username_is_reserved(user.username):
			raise UsernameCannotContainNextthoughtCom(_("That username is not valid. Please choose another."), 'Username', user.username, value=user.username)

		self._check_name(user)

		# As of 2012-10-01, the acct creation UI has two very anglocentric fields labeled distinctly
		# 'first' and 'last' name, which it concats to form the 'realname'. So this makes
		# realname and alias exactly the same. As of this same date, we are also never returning
		# the realname value to any site, nor are we searching on it.

		profile = user_interfaces.IUserProfile(user)
		birthdate = getattr(profile, 'birthdate', None)
		if birthdate:
			if birthdate >= datetime.date.today():
				raise BirthdateInFuture(_("Birthdate must be in the past."), 'birthdate', birthdate.isoformat(), value=birthdate)

			if not _is_x_or_more_years_ago(birthdate, 4):
				raise BirthdateTooRecent(_("Birthdate must be at least four years ago."), 'birthdate', birthdate.isoformat(), value=birthdate)

			if _is_x_or_more_years_ago(birthdate, 150):
				raise BirthdateTooAncient(_("Birthdate must be less than 150 years ago."), 'birthdate', birthdate.isoformat(), value=birthdate)


@interface.implementer(ISitePolicyUserEventListener)
class GenericKidSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements the starting policy for the sites with kids.

	.. note:: This site policy has a dependency between username and realname
		values. To disable this dependency during preflight checking,
		use exactly the placeholder objects defined in this policy.
	"""

	IF_ROOT = nti_interfaces.ICoppaUser
	IF_WITH_AGREEMENT = nti_interfaces.ICoppaUserWithAgreement
	IF_WOUT_AGREEMENT = nti_interfaces.ICoppaUserWithoutAgreement
	IF_WITH_AGREEMENT_UPGRADED = nti_interfaces.ICoppaUserWithAgreementUpgraded

	PLACEHOLDER_USERNAME = 'A_Username_We_Allow_That_Doesnt_Conflict'
	PLACEHOLDER_REALNAME = 'com.nextthought.account_creation_user WithALastName'


	def upgrade_user(self, user):
		if not self.IF_WOUT_AGREEMENT.providedBy(user):
			logger.debug("No need to upgrade user %s that doesn't provide %s", user, self.IF_WOUT_AGREEMENT)
			return False

		# Copy the profile info. First, adapt to the old profile:
		orig_profile = user_interfaces.IUserProfile(user)
		# Then adjust the interfaces
		interface.noLongerProvides(user, self.IF_WOUT_AGREEMENT)
		interface.alsoProvides(user, self.IF_WITH_AGREEMENT_UPGRADED)
		# Now get the new profile
		new_profile = user_interfaces.IUserProfile(user)
		# If they changed, adjust them, copying in any missing data
		if orig_profile is not new_profile:
			most_derived_profile_iface = find_most_derived_interface(new_profile, user_interfaces.IUserProfile)
			for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
				if interface.interfaces.IMethod.providedBy(field):
					continue

				if getattr(orig_profile, name, None):  # Only copy things that have values. Let defaults be used otherwise
					setattr(new_profile, name, getattr(orig_profile, name))

		# user.transitionTime = time.time()

		notify(app_interfaces.UserUpgradedEvent(user,
												restricted_interface=self.IF_WOUT_AGREEMENT, restricted_profile=orig_profile,
												upgraded_interface=self.IF_WITH_AGREEMENT, upgraded_profile=new_profile,
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

		if event.ext_value.get('birthdate') and _is_thirteen_or_more_years_ago(IDate(event.ext_value['birthdate'])):
			iface_to_provide = self.IF_WITH_AGREEMENT
		elif 'contact_email' in event.ext_value and 'email' not in event.ext_value:
			event.ext_value['email'] = event.ext_value['contact_email']

		interface.alsoProvides(user, iface_to_provide)

	def user_created(self, user, event):
		"""
		Makes the user immutably named.
		"""
		super(GenericKidSitePolicyEventListener, self).user_created(user, event)

		interface.alsoProvides(user, user_interfaces.IImmutableFriendlyNamed)

	def user_will_create(self, user, event):
		super(GenericKidSitePolicyEventListener, self).user_will_create(user, event)
		names = user_interfaces.IFriendlyNamed(user)
		# Force the alias to be the same as the username
		names.alias = user.username
		# Match the format of, e.g, WrongTypeError: message, field/type, value
		# the view likes this

		# We require a realname, at least the first name, it must already be given.
		# parse it now. This raises BlankHumanName if missing. This was checked by super
		human_name = nameparser.HumanName(names.realname)

		# Disable username/realname dependency checking if we are using placeholder data
		if user.username is not self.PLACEHOLDER_USERNAME:
			human_name_parts = human_name.first_list + human_name.middle_list + human_name.last_list
			if any((x.lower() in user.username.lower() for x in human_name_parts)):
				raise UsernameCannotContainRealname(
					_("Username ${username} cannot include any part of the real name ${realname}.",
					  mapping={'username': user.username, 'realname': names.realname}),
					'Username', user.username, value=user.username, field='Username')

		if '@' in user.username:
			raise UsernameCannotContainAt(user.username, user.ALLOWED_USERNAME_CHARS).new_instance_restricting_chars('@')

		# This much is handled in the will_update_event
		# profile = user_interfaces.IUserProfile( user )
		# if profile.birthdate and _is_thirteen_or_more_years_ago( profile.birthdate ):
			# If we can show the kid is actually at least 13, then
			# we don't need to get an agreement

		if nti_interfaces.ICoppaUserWithoutAgreement.providedBy(user):
			# We can only store the first name for little kids
			names.realname = human_name.first

	def map_validation_exception(self, incoming_data, exception):
		if type(exception) == user_interfaces.UsernameContainsIllegalChar:
			return exception.new_instance_restricting_chars('@')
		return exception


@interface.implementer(ISitePolicyUserEventListener)
class GenericAdultSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements a generic policy for adult sites.
	"""

	def user_created(self, user, event):
		super(GenericAdultSitePolicyEventListener, self).user_created(user, event)
		interface.alsoProvides(user, user_interfaces.IImmutableFriendlyNamed)

	def user_will_update_new(self, user, event):
		"""
		Also enforces the email requirement constraint for newly created objects.
		"""
		super(GenericAdultSitePolicyEventListener, self).user_will_update_new(user, event)
		ext_value = getattr(event, 'ext_value', {})
		if 'email' not in ext_value and '@' in ext_value.get('Username', ''):
			ext_value['email'] = ext_value['Username']

	def user_will_create(self, user, event):
		"""
		This policy verifies naming restraints.

		"""
		super(GenericAdultSitePolicyEventListener, self).user_will_create(user, event)

		profile = user_interfaces.IUserProfile(user)
		if '@' in user.username:
			try:
				user_interfaces.checkEmailAddress(user.username)
			except user_interfaces.EmailAddressInvalid:
				# If the username is not a valid email address,
				# nothing further is required.
				pass
			else:
				# If it is a valid email address, it must match the
				# email
				email = getattr(profile, 'email', None)
				if not email:
					profile.email = user.username
				elif user.username != email:
					raise AtInUsernameImpliesMatchingEmail("If you want to use an email address for the username, it must match the email address you enter", 'Username', user.username)


# Profiles for MC

# TODO: These need to move to the mathcounts site package.
# But be careful for BWC.
# XXX: Note: It appears we've lost all profile data on that site at least once
# already
@component.adapter(IMathcountsCoppaUserWithoutAgreement)
@interface.implementer(IMathcountsCoppaUserWithoutAgreementUserProfile)
class MathcountsCoppaUserWithoutAgreementUserProfile(user_profile.RestrictedUserProfileWithContactEmail):
	pass

@component.adapter(IMathcountsCoppaUserWithAgreement)
@interface.implementer(IMathcountsCoppaUserWithAgreementUserProfile)
class MathcountsCoppaUserWithAgreementUserProfile(user_profile.EmailRequiredUserProfile):
	pass

user_profile.add_profile_fields(IMathcountsCoppaUserWithoutAgreementUserProfile, MathcountsCoppaUserWithoutAgreementUserProfile)
del MathcountsCoppaUserWithoutAgreementUserProfile.email  # But restore the behaviour from the super
user_profile.add_profile_fields(IMathcountsCoppaUserWithAgreementUserProfile, MathcountsCoppaUserWithAgreementUserProfile)

MathcountsCoppaUserWithoutAgreementUserProfileFactory = zope.annotation.factory(MathcountsCoppaUserWithoutAgreementUserProfile)
MathcountsCoppaUserWithAgreementUserProfileFactory = zope.annotation.factory(MathcountsCoppaUserWithAgreementUserProfile)


@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
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

@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class NoDFLCapabilityFilter(NoAvatarUploadCapabilityFilter):
	"""
	Removes the ability to create DFLs.
	"""

	def filterCapabilities(self, capabilities):
		result = super(NoDFLCapabilityFilter, self).filterCapabilities(capabilities)
		result.discard('nti.platform.p2p.dynamicfriendslists')
		return result

@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class NoChatAvatarDFLCapabilityFilter(NoDFLCapabilityFilter):
	"""
	Removes chat.
	"""

	def filterCapabilities(self, capabilities):
		result = super(NoChatAvatarDFLCapabilityFilter, self).filterCapabilities(capabilities)
		result.discard('nti.platform.p2p.chat')
		return result


@interface.implementer(ISitePolicyUserEventListener)
class AdultCommunitySitePolicyEventListener(GenericAdultSitePolicyEventListener):
	"""
	Implements the policy for an adult site, adding new users to a single community.
	"""

	COM_USERNAME = None
	COM_ALIAS = None
	COM_REALNAME = None

	def user_created(self, user, event):
		"""
		This policy places newly created users in the community defined by the fields
		of this object (creating it if it doesn't exist).

		"""
		super(AdultCommunitySitePolicyEventListener, self).user_created(user, event)
		self._join_community_user_created(user, event)


@interface.implementer(ISitePolicyUserEventListener)
class RwandaSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for the rwanda site.
	"""

	COM_USERNAME = 'CarnegieMellonUniversity'
	COM_ALIAS = 'CMU'
	COM_REALNAME = 'Carnegie Mellon University'

@interface.implementer(ISitePolicyUserEventListener)
class LawSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``law.nextthought.com``.
	"""

	COM_USERNAME = 'law.nextthought.com'
	COM_ALIAS = 'Law'
	COM_REALNAME = 'Legal Studies'

@interface.implementer(ISitePolicyUserEventListener)
class PrmiaSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``prmia.nextthought.com``.
	"""

	LANDING_PAGE_NTIID = b'tag:nextthought.com,2011-10:PRMIA-HTML-PRMIA_RiskCourse.advanced_stress_testing_for_financial_institutions'

	COM_USERNAME = 'prmia.nextthought.com'
	COM_ALIAS = 'PRMIA'
	COM_REALNAME = "Professional Risk Managers' International Association"


@interface.implementer(ISitePolicyUserEventListener)
class CollegiateSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for the Collegiate site.
	"""

	COM_USERNAME = 'collegiate.nextthought.com'
	COM_ALIAS = 'Collegiate'
	COM_REALNAME = 'Collegiate'

@interface.implementer(ISitePolicyUserEventListener)
class GloriaMundiSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for the Gloria-Mundi site.
	"""

	COM_USERNAME = 'gloria-mundi.nextthought.com'
	COM_ALIAS = 'Gloria-Mundi'
	COM_REALNAME = 'Gloria-Mundi'

	def user_created(self, user, event):
		super(GloriaMundiSitePolicyEventListener, self).user_created(user, event)
		# These people cannot be bothered to type in their own invitation
		# code, so do it for them. Do it this way so that all the right events
		# fire.
		owner = users.User.get_user('barrynschachter@gmail.com')
		import numbers
		for obj in owner.friendsLists.values():
			if isinstance(obj, numbers.Number):
				logger.warn("Collection %s in user %s has old numeric data in values", owner.friendsLists, owner)
				continue
			if obj.username == 'Basel-OTC-Margin' or user_interfaces.IFriendlyNamed(obj).alias == 'Basel-OTC-Margin' or user_interfaces.IFriendlyNamed(obj).realname == 'Basel-OTC-Margin':
				from nti.appserver.invitations import interfaces as invite_interfaces
				from nti.appserver.invitations.utility import accept_invitations
				invitations = component.getUtility(invite_interfaces.IInvitations)
				code = invitations._getDefaultInvitationCode(obj)  # Yup, private method.
				accept_invitations(user, [code])

@interface.implementer(ISitePolicyUserEventListener)
class FintechSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``fintech.nextthought.com``.
	"""

	LANDING_PAGE_NTIID = b'tag:nextthought.com,2011-10:PRMIA-HTML-FinTech_PRMIA_RiskCourseSample.framework_for_diagnosing_systemic_risk'

	COM_USERNAME = 'fintech.nextthought.com'
	COM_ALIAS = 'FinTech'
	COM_REALNAME = 'FinTech'

	DFL_NAME = u'prm candidate group'
	DFL_OWNER = u'fintechken'

	def user_created(self, user, event):
		super(FintechSitePolicyEventListener, self).user_created(user, event)
		nti_interfaces.IWeakRef(user)
		owner = users.User.get_user(self.DFL_OWNER)
		friendsLists = getattr(owner, 'friendsLists', {})
		for fl in friendsLists.values():
			if not nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(fl):
				continue
			names = user_interfaces.IFriendlyNamed(fl)
			if self.DFL_NAME in (fl.username.lower(), (names.realname or '').lower(), (names.alias or '').lower()):
				fl.addFriend(user)
				logger.info("User '%s' added to DFL '%s" % (user, self.DFL_NAME))
				break

#OU site policies
# XXX: Deprecated and going away. moved to nti.app.products.ou
@interface.implementer(ISitePolicyUserEventListener)
class OUSitePolicyEventListener(AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``platform.ou.edu``.
	"""

	NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = 'new_user_created_ou'
	NEW_USER_CREATED_EMAIL_SUBJECT = _("Welcome to the OU Digital Course Platform")

	COM_USERNAME = 'ou.nextthought.com'
	COM_ALIAS = 'OU'
	COM_REALNAME = "The University of Oklahoma"

	def _censor_usernames(self, user):
		pass

	def user_will_create(self, user, event):
		meta_data = getattr(event, 'meta_data', None) or {}

		# check if username is a 4x4
		if meta_data.get('check_4x4', True) and re.match('[a-zA-z]{2,4}[0-9]{4}', user.username):
			raise InvalidUsernamePattern(_("The username is not allowed. Please choose another."),
										'Username', user.username, value=user.username)
		# continue w/ validation
		super(OUSitePolicyEventListener, self).user_will_create(user, event)

	def _check_name(self, user):
		names = user_interfaces.IFriendlyNamed(user)
		if names.realname is None or not names.realname.strip():
			raise nameparser.parser.BlankHumanNameError()
		human_name = names.realname
		names.alias = names.realname = unicode(human_name)

@interface.implementer(ISitePolicyUserEventListener)
class OUTestSitePolicyEventListener(OUSitePolicyEventListener):
	"""
	Implements the policy for the ou test site.
	"""

	COM_USERNAME = 'ou.nextthought.com'
	COM_ALIAS = '*OU*'
	COM_REALNAME = '*The University of Oklahoma*'


###
# Columbia site profiles.
# These are somewhat special in that the users may already have an existing adult profile,
# from a non-columbia site, and when asked for their new profile, we want to be able to provide
# one with all the right data. In some ways, this is similar to upgrading a COPPA account.
# NOTE: This is a one-time copy; if the user logs in to another site, they will see
# their non-columbia profile data, which can be updated separately, which is weird.
# (TODO: Is their anything weird with the user indexes that can happen with this?)
###

@component.adapter(nti_interfaces.IUser)
@interface.implementer(IColumbiaBusinessUserProfile)
class ColumbiaBusinessUserProfile(user_profile.EmailRequiredUserProfile):
	pass

user_profile.add_profile_fields(IColumbiaBusinessUserProfile, ColumbiaBusinessUserProfile)

@component.adapter(nti_interfaces.IUser)
@interface.implementer(IColumbiaBusinessUserProfile)
def ColumbiaBusinessUserProfileFactory(context):
	# The special logic to look for a profile under a *different* annotation key,
	# and if found, copy it to the new data.
	# (Depending on whether we are in dev mode or not, we could have two different keys)
	columbia_profile_key = 'nti.appserver.site_policies.ColumbiaBusinessUserProfile'  # BWC
	annotations = zope.annotation.interfaces.IAnnotations(context)
	try:
		return annotations[columbia_profile_key]
		#Yes, it already existed!
	except KeyError:
		# Nuts. Start with a fresh columbia profile
		columbia_profile = zope.annotation.factory(ColumbiaBusinessUserProfile, key=columbia_profile_key)(context)
		# Do we need to migrate anything?
		for old_key in user_profile.EMAIL_REQUIRED_USER_PROFILE_KEY, user_profile.COMPLETE_USER_PROFILE_KEY:
			old_prof = annotations.get( old_key )
			if old_prof is not None:
				old_prof._p_activate() # because we access the dict directly
				old_data = old_prof.__dict__
				for k, v in old_data.items():
					if not k.startswith( '_p' ) and not k.startswith( '_v' ) and not k in ('__parent__', '__name__'):
						columbia_profile.__dict__[k] = v
				columbia_profile._p_changed = True
				break
		return columbia_profile

####
# Make sure we load views from any registered site.
####
@interface.implementer(app_interfaces.IViewConfigurator)
class _SiteViewConfigurator(object):
	"""
	Load any views that belong to an specific site
	"""
	# DEPRECATED: Do this with pyramid.zcml
	def add_views(self, config):
		for site in sites._find_sites():
			for _, mapper in site.getUtilitiesFor(app_interfaces.ISiteViewConfigurator):
				mapper.add_views(config)
