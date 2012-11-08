#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Policies and components that are related to the dynamic site of the request. Because the dataserver
itself may actually be a single domain, the HTTP `Origin <http://tools.ietf.org/html/rfc6454>`_ header is first
checked before the site. These policies are by nature tied to the existence
of a request.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
from . import MessageFactory as _

from zope import component
from zope import interface
from zope import schema
from zope.event import notify

from pyramid.threadlocal import get_current_request

from nti.contentlibrary import interfaces as lib_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.externalization import interfaces as ext_interfaces

from nti.contentfragments import censor
from nti.utils.schema import InvalidValue
from nti.utils.schema import find_most_derived_interface

from nti.dataserver import shards as nti_shards

from ._email_utils import queue_simple_html_text_email

import nameparser
import datetime
import urllib
import string

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
	if not request: # pragma: no cover
		return () if not include_default else ('',)

	result = []

	if 'origin' in request.headers:
		# TODO: The port splitting breaks on IPv6
		# Origin comes in as a complete URL, host and potentially port
		# Sometimes it comes in blank (unit tests, mostly, that don't use proper HTTP libraries)
		# so the below is robust against that, as well as deliberately malformed input
		origin = request.headers['origin']
		__traceback_info__ = origin
		if origin and '//' in origin and ':' in origin:
			host = origin.split( '//' )[1].split( ":" )[0]
			result.append( host.lower() )
	if request.host:
		# Host is a plain name/IP address, and potentially port
		result.append( request.host.split(':')[0].lower() )

	for blacklisted in ('localhost', '0.0.0.0'):
		if blacklisted in result:
			result.remove( blacklisted )

	if include_default:
		result.append( '' )
	return result

_marker = object()
def queryAdapterInSite( obj, target, request=None, site_names=None, default=None, context=None  ):
	"""
	Queries for named adapters following the site names, all the way up until the default
	site name.

	:keyword request: The current request to investigate for site names.
		If not given, the threadlocal request will be used.
	:keyword site_names: If given and non-empty, the list of site names to use.
		Overrides the `request` parameter.
	"""

	site_names = get_possible_site_names(request, include_default=True)

	for site in site_names:
		result = component.queryAdapter( obj, target, name=site, context=context, default=_marker )
		if result is not _marker:
			return result
	return default

def queryMultiAdapterInSite( objects, target, request=None, site_names=None, default=None, context=None  ):
	"""
	Queries for named adapters following the site names, all the way up until the default
	site name.

	:keyword request: The current request to investigate for site names.
		If not given, the threadlocal request will be used.
	:keyword site_names: If given and non-empty, the list of site names to use.
		Overrides the `request` parameter.

	"""
	site_names = site_names or get_possible_site_names(request, include_default=True)

	for site in site_names:
		result = component.queryMultiAdapter( objects, target, name=site, context=context, default=_marker )
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

 	def __init__( self, key ):
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

	def placeNewUser( self, user, users_directory, shards ):
		placed = False
		for site_name in get_possible_site_names():
			placer = component.queryUtility( nti_interfaces.INewUserPlacer, name=site_name )
			if placer:
				placed = True
				placer.placeNewUser( user, users_directory, shards )
			elif site_name in shards:
				placed = self.place_user_in_shard_named( user, users_directory, site_name )

			if placed:
				break

		if not placed:
			component.getUtility( nti_interfaces.INewUserPlacer, name='default' ).placeNewUser( user, users_directory, shards )

####
## Handling events within particular sites
#
# TODO: It's not clear what the best way is to handle this. We have a
# few options.
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
# This is starting to get out of hand, though, and the automatic delegation of a real site
# would be very nice to have. The `EventListener` is now being delegated to for all kinds
# of random things, many of which have nothing to do with events, such as
# object externalization decoration
####

class ISitePolicyUserEventListener(interface.Interface):
	"""
	Register instances of these as utilities by the name of the site
	they should apply to.
	"""

	def map_validation_exception( incoming_data, exception ):
		"""
		Gives a site policy a chance to change an exception being returned
		during validation.
		"""

	def user_will_update_new( user, event ):
		"""
		Handler for the IWillUpdateNewEntityEvent, called
		before creation is complete or the user is updated.
		"""

	def user_created( user, event ):
		"""
		Called when a user is created.
		"""

	def user_created_with_request( user, event ):
		"""
		Called when a user is created in the scope of an interactive
		request (after user_created).
		"""

	def user_will_create( user, event ):
		"""
		Called just before a user is created. Do most validation here.
		"""

	# TODO : I'm not entirely sure this belongs here. Might want to rethink this a lot
	def upgrade_user( user ):
		"""
		Transition a user from a limited form to the next lest limited forrm.
		Specifically intended to deal with providing coppa consent.
		"""


from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from nti.dataserver import users
import zope.schema

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class SiteBasedExternalObjectDecorator(object):
	"""
	Something that can be registered as a subscriber to forward
	object decoration to objects that do something for a particular site.
	These object must be registered as multi-adapters for the original object
	and the active request, and must be named for the site.

	Register this object sparingly, it is expensive.
	"""

	def __init__( self, *args ):
		pass

	def decorateExternalObject( self, orig_obj, result ):
		request = get_current_request()
		if not request:
			return

		for site_name in get_possible_site_names( include_default=None ):
			adapter = component.queryMultiAdapter( (orig_obj, request), ext_interfaces.IExternalObjectDecorator, name=site_name )
			if adapter:
				adapter.decorateExternalObject( orig_obj, result )
				break

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class LogonLinksCreationStripper(object):
	"""
	Configured for sites that are not allowing account creation through the UI.
	"""

	def __init__( self, *args ):
		pass

	def decorateExternalObject( self, orig_obj, result ):
		result['Links'] = [link for link in result['Links'] if link['rel'] not in ('account.create', 'account.preflight.create')]


def find_site_policy( request=None ):
	"""
	Find a site policy that's currently active, including the default.

	:return: A two-tuple of (policy, site_name). If no policy was found
		then the first value is None and the second value is all applicable site_names found.
	"""
	site_names = get_possible_site_names( request=request, include_default=True )
	for site_name in site_names:
		utility = component.queryUtility( ISitePolicyUserEventListener, name=site_name )
		if utility:
			return utility, site_name
	return None, site_names

def _dispatch_to_policy( user, event, func_name ):
	"""
	Returns a true value if the event was handled by some policy.
	"""
	utility, site_name = find_site_policy( )
	if utility:
		logger.info( "Site %s wants to handle user creation event %s for %s with %s", site_name, func_name, user, utility )
		getattr( utility, func_name )( user, event )
		return True

	logger.info( "No site in %s wanted to handle user event %s for %s", site_name, func_name, user )


@component.adapter(nti_interfaces.IUser,IObjectCreatedEvent)
def dispatch_user_created_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_created' )

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillUpdateNewEntityEvent)
def dispatch_user_will_update_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_will_update_new' )

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillCreateNewEntityEvent)
def dispatch_user_will_create_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_will_create' )

@component.adapter(nti_interfaces.IUser, app_interfaces.IUserCreatedWithRequestEvent)
def dispatch_user_created_with_request_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_created_with_request' )

def _censor_usernames( entity, event=None ):
	"""
	Censore the username field of the entity. Can be used as an event listener as well.
	"""
	policy = censor.DefaultCensoredContentPolicy()

	if policy.censor( entity.username, entity ) != entity.username:
		raise FieldContainsCensoredSequence( _("Username contains a censored sequence"), 'Username', entity.username )

	names = user_interfaces.IFriendlyNamed( entity, None )
	if names and names.alias: # TODO: What about realname?
		if policy.censor( names.alias, entity ) != names.alias:
			raise FieldContainsCensoredSequence( _("Alias contains a censored sequence"), 'alias', names.alias )

def _is_x_or_more_years_ago( birthdate, years_ago=13 ):

	today = datetime.date.today()
	x_years_ago = datetime.date.today().replace( year=today.year - years_ago )

	return birthdate < x_years_ago

_is_thirteen_or_more_years_ago = _is_x_or_more_years_ago

# Validation errors. The class names will be used as codes,
# which will help the UI if they don't want to use our error
# messages
class BirthdateInFuture(InvalidValue): pass
class BirthdateTooRecent(InvalidValue): pass
class BirthdateTooAncient(InvalidValue): pass
class UsernameCannotContainRealname(InvalidValue): pass
class UsernameCannotContainAt(user_interfaces.UsernameContainsIllegalChar): pass
class UsernameCannotContainNextthoughtCom(InvalidValue): pass
class FieldContainsCensoredSequence(InvalidValue): pass
class MissingFirstName(zope.schema.interfaces.RequiredMissing):
	field = 'realname'
class MissingLastName(zope.schema.interfaces.RequiredMissing):
	field = 'realname'
class AtInUsernameImpliesMatchingEmail(InvalidValue): pass

@interface.implementer(ISitePolicyUserEventListener)
class GenericSitePolicyEventListener(object):
	"""
	Implements a generic policy for all sites.
	"""

	def user_created_with_request( self, user, event ):
		self._send_email_on_new_account( user, event )

	NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = 'new_user_created'

	def _send_email_on_new_account( self, user, event ):
		"""
		For new accounts where we have an email (and of course the request), we send a welcome message.

		Notice that we do not have an email collected for the ICoppaUserWithoutAgreement, so
		they will never get a notice here. (And we don't have to specifically check for that).

		Uses the self/class attribute ``NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME`` to generate the email text.
		"""

		if not event.request: #pragma: no cover
			return

		profile = user_interfaces.IUserProfile( user )
		email = getattr( profile, 'email' )
		if not email:
			return

		# Need to send both HTML and plain text if we send HTML, because
		# many clients still do not render HTML emails well (e.g., the popup notification on iOS
		# only works with a text part)
		queue_simple_html_text_email( self.NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME,
									  subject=_("Welcome to NextThought"),
									  recipients=[email],
									  template_args={'user': user, 'profile': profile, 'context': user },
									  request=event.request )

	def map_validation_exception( self, incoming_data, exception ):
		return exception

	def upgrade_user( self, user ):
		pass

	def user_will_update_new( self, user, event ):
		pass

	def user_created( self, user, event ):
		pass

	def user_will_create( self, user, event ):
		"""
		This policy verifies naming restraints.

		"""
		_censor_usernames( user )
		if user.username.endswith( '@nextthought.com' ) or user.username in (nti_interfaces.SYSTEM_USER_NAME, nti_interfaces.SYSTEM_USER_ID):
			raise UsernameCannotContainNextthoughtCom( _("That username is not valid. Please choose another."), 'Username', user.username, value=user.username )

		# Icky. For some random reason we require everyone to provide their real name,
		# and we force the display name to be derived from it.
		names = user_interfaces.IFriendlyNamed( user )
		human_name = nameparser.HumanName( names.realname ) # Raises BlankHumanName if missing
		if not human_name.first:
			raise MissingFirstName( _("Please provide your first name."), 'realname', names.realname )
		if not human_name.last:
			raise MissingLastName( _("Please provide your last name."), 'realname', names.realname )
		human_name.capitalize()
		names.realname = unicode(human_name)
		names.alias = human_name.first + ' ' + human_name.last
		# As of 2012-10-01, the acct creation UI has two very anglocentric fields labeled distinctly
		# 'first' and 'last' name, which it concats to form the 'realname'. So this makes
		# realname and alias exactly the same. As of this same date, we are also never returning
		# the realname value to any site, nor are we searching on it.

		profile = user_interfaces.IUserProfile( user )
		birthdate = getattr( profile, 'birthdate', None )
		if birthdate:
			if birthdate >= datetime.date.today():
				raise BirthdateInFuture( _("Birthdate must be in the past."), 'birthdate', birthdate.isoformat(), value=birthdate )

			if not _is_x_or_more_years_ago( birthdate, 4 ):
				raise BirthdateTooRecent( _("Birthdate must be at least four years ago."), 'birthdate', birthdate.isoformat(), value=birthdate )

			if _is_x_or_more_years_ago( birthdate, 150 ):
				raise BirthdateTooAncient( _("Birthdate must be less than 150 years ago."), 'birthdate', birthdate.isoformat(), value=birthdate )


@interface.implementer(ISitePolicyUserEventListener)
class GenericKidSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements the starting policy for the sites with kids.
	"""

	IF_ROOT = nti_interfaces.ICoppaUser
	IF_WITH_AGREEMENT = nti_interfaces.ICoppaUserWithAgreement
	IF_WOUT_AGREEMENT = nti_interfaces.ICoppaUserWithoutAgreement

	def upgrade_user( self, user ):
		if not self.IF_WOUT_AGREEMENT.providedBy( user ):
			logger.debug( "No need to upgrade user %s that doesn't provide %s", user, self.IF_WOUT_AGREEMENT )
			return

		# Copy the profile info. First, adapt to the old profile:
		orig_profile = user_interfaces.IUserProfile( user )
		# Then adjust the interfaces
		interface.noLongerProvides( user, self.IF_WOUT_AGREEMENT )
		interface.alsoProvides( user, self.IF_WITH_AGREEMENT )
		# Now get the new profile
		new_profile = user_interfaces.IUserProfile( user )
		# If they changed, adjust them, copying in any missing data
		if orig_profile is not new_profile:
			most_derived_profile_iface = find_most_derived_interface( new_profile, user_interfaces.IUserProfile )
			for name, field in most_derived_profile_iface.namesAndDescriptions(all=True):
				if interface.interfaces.IMethod.providedBy( field ):
					continue

				if getattr( orig_profile, name, None ): # Only copy things that have values. Let defaults be used otherwise
					setattr( new_profile, name, getattr( orig_profile, name ) )
		notify( app_interfaces.UserUpgradedEvent( user,
												  restricted_interface=self.IF_WOUT_AGREEMENT, restricted_profile=orig_profile,
												  upgraded_interface=self.IF_WITH_AGREEMENT, upgraded_profile=new_profile,
												  request=get_current_request() ) )
		# TODO: If the new profile required some values the old one didn't, then what?
		# Prime example: email, not required for kids, yes required for adults.

	def user_will_update_new( self, user, event ):
		"""
		This policy applies the :class:`nti.dataserver.interfaces.ICoppaUserWithoutAgreement` or
		the :class:`nti.dataserver.interfaces.ICoppaUserWithAgreement` interface
		to the object, which drives the available data to store.
		"""

		interface.alsoProvides( user, self.IF_ROOT )
		iface_to_provide = self.IF_WOUT_AGREEMENT

		if event.ext_value.get( 'birthdate' ) and _is_thirteen_or_more_years_ago( zope.interface.common.idatetime.IDate( event.ext_value['birthdate'] ) ):
			iface_to_provide = self.IF_WITH_AGREEMENT
		elif 'contact_email' in event.ext_value and 'email' not in event.ext_value:
			event.ext_value['email'] = event.ext_value['contact_email']

		interface.alsoProvides( user, iface_to_provide )

	def user_created( self, user, event ):
		"""
		Makes the user immutably named.
		"""
		super(GenericKidSitePolicyEventListener,self).user_created( user, event )

		interface.alsoProvides( user, user_interfaces.IImmutableFriendlyNamed )

	def user_will_create( self, user, event ):
		super(GenericKidSitePolicyEventListener,self).user_will_create( user, event )
		names = user_interfaces.IFriendlyNamed( user )
		# Force the alias to be the same as the username
		names.alias = user.username
		# Match the format of, e.g, WrongTypeError: message, field/type, value
		# the view likes this

		# We require a realname, at least the first name, it must already be given.
		# parse it now. This raises BlankHumanName if missing. This was checked by super
		human_name = nameparser.HumanName( names.realname )

		human_name_parts = human_name.first_list + human_name.middle_list + human_name.last_list
		if any( (x.lower() in user.username.lower() for x in human_name_parts) ):
			raise UsernameCannotContainRealname("Username %s cannot include any part of the real name %s" % # TODO: I18N
												(user.username, names.realname), 'Username', user.username, value=user.username, field='Username' )

		if '@' in user.username:
			raise UsernameCannotContainAt( user.username, user.ALLOWED_USERNAME_CHARS ).new_instance_restricting_chars( '@' )

		# This much is handled in the will_update_event
		#profile = user_interfaces.IUserProfile( user )
		#if profile.birthdate and _is_thirteen_or_more_years_ago( profile.birthdate ):
			# If we can show the kid is actually at least 13, then
			# we don't need to get an agreement

		if nti_interfaces.ICoppaUserWithoutAgreement.providedBy( user ):
			# We can only store the first name for little kids
			names.realname = human_name.first

	def map_validation_exception( self, incoming_data, exception ):
		if type(exception) == user_interfaces.UsernameContainsIllegalChar:
			return exception.new_instance_restricting_chars( '@' )
		return exception


@interface.implementer(ISitePolicyUserEventListener)
class GenericAdultSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements a generic policy for adult sites.
	"""

	def user_created( self, user, event ):
		super(GenericAdultSitePolicyEventListener,self).user_created( user, event )
		interface.alsoProvides( user, user_interfaces.IImmutableFriendlyNamed )

	def user_will_update_new( self, user, event ):
		"""
		Also enforces the email requirement constraint for newly created objects.
		"""
		super(GenericAdultSitePolicyEventListener,self).user_will_update_new( user, event )
		ext_value = event.ext_value
		if 'email' not in ext_value and '@' in ext_value.get( 'Username', '' ):
			ext_value['email'] = ext_value['Username']

	def user_will_create( self, user, event ):
		"""
		This policy verifies naming restraints.

		"""
		super(GenericAdultSitePolicyEventListener,self).user_will_create( user, event )

		profile = user_interfaces.IUserProfile( user )
		if '@' in user.username:
			email = getattr(profile, 'email', None)
			if not email:
				profile.email = user.username
			elif user.username != email:
				raise AtInUsernameImpliesMatchingEmail( "If you want to use an email address for the username, it must match the email address you enter", 'Username', user.username )

class IMathcountsUser(nti_interfaces.ICoppaUser):
	pass

class IMathcountsCoppaUserWithoutAgreement(IMathcountsUser, nti_interfaces.ICoppaUserWithoutAgreement):
	pass
class IMathcountsCoppaUserWithAgreement(IMathcountsUser, nti_interfaces.ICoppaUserWithAgreement):
	pass

# Profiles for MC
from nti.dataserver.users import user_profile
from nti.utils.schema import ValidTextLine
import zope.annotation

class IMathcountsCoppaUserWithoutAgreementUserProfile(user_interfaces.IRestrictedUserProfileWithContactEmail):

	participates_in_mathcounts = schema.Bool(
		title="Do you currently participate in MATHCOUNTS?",
		required=False,
		default=False )

	password_recovery_email_hash = ValidTextLine(
		title="A secure hash of an email address used during password recovery",
		description="Typically auto-generated by setting the `email` field.",
		required=True )

	email = ValidTextLine(
		title='Email',
		description=u'Email is not stored at this level, but the field is specified here as a convenient way'
			' to be able to set the password_recovery_email_hash',
		required=False, # But we require it in the UI to get the recovery
		constraint=user_interfaces.checkEmailAddress)

	# No affiliation
	# No role
IMathcountsCoppaUserWithoutAgreementUserProfile['email'].setTaggedValue( user_interfaces.TAG_REQUIRED_IN_UI, True )
IMathcountsCoppaUserWithoutAgreementUserProfile['password_recovery_email_hash'].setTaggedValue( user_interfaces.TAG_HIDDEN_IN_UI, True )

class IMathcountsCoppaUserWithAgreementUserProfile(user_interfaces.IEmailRequiredUserProfile):

	participates_in_mathcounts = schema.Bool(
		title="Do you currently participate in MATHCOUNTS?",
		required=False,
		default=False )

	affiliation = schema.TextLine(
		title='Affiliation',
		description="Your affiliation, such as school name",
		required=False)

	role = schema.Choice( title="Your role in the organization",
						  values=("Student", "Teacher", "Coach", "Parent", "Volunteer", "Other"),
						  default="Other",
						  required=False)

	# When we upgrade accounts, we need to keep the contact email
	contact_email = ValidTextLine(
		title='Contact email',
		description=u"An email address to use to contact someone responsible for this accounts' user",
		required=False,
		constraint=user_interfaces.checkEmailAddress)

IMathcountsCoppaUserWithAgreementUserProfile['affiliation'].setTaggedValue( user_interfaces.TAG_UI_TYPE, 'nti.appserver.site_policies.school' )
IMathcountsCoppaUserWithAgreementUserProfile['affiliation'].setTaggedValue( user_interfaces.TAG_READONLY_IN_UI, True ) # post-creation
IMathcountsCoppaUserWithAgreementUserProfile['role'].setTaggedValue( user_interfaces.TAG_READONLY_IN_UI, True ) # post-creation
IMathcountsCoppaUserWithAgreementUserProfile['contact_email'].setTaggedValue( user_interfaces.TAG_HIDDEN_IN_UI, True )

@component.adapter(IMathcountsCoppaUserWithoutAgreement)
@interface.implementer(IMathcountsCoppaUserWithoutAgreementUserProfile)
class MathcountsCoppaUserWithoutAgreementUserProfile(user_profile.RestrictedUserProfileWithContactEmail):
	pass

@component.adapter(IMathcountsCoppaUserWithAgreement)
@interface.implementer(IMathcountsCoppaUserWithAgreementUserProfile)
class MathcountsCoppaUserWithAgreementUserProfile(user_profile.EmailRequiredUserProfile):
	pass

user_profile.add_profile_fields( IMathcountsCoppaUserWithoutAgreementUserProfile, MathcountsCoppaUserWithoutAgreementUserProfile )
del MathcountsCoppaUserWithoutAgreementUserProfile.email # But restore the behaviour from the super
user_profile.add_profile_fields( IMathcountsCoppaUserWithAgreementUserProfile, MathcountsCoppaUserWithAgreementUserProfile )

MathcountsCoppaUserWithoutAgreementUserProfileFactory = zope.annotation.factory( MathcountsCoppaUserWithoutAgreementUserProfile )
MathcountsCoppaUserWithAgreementUserProfileFactory = zope.annotation.factory( MathcountsCoppaUserWithAgreementUserProfile )

def _join_community_user_created( self, user, event ):
	"""
	Helper method that places newly created users in the community defined by the fields
	of this object (creating it if it doesn't exist).
	"""
	if self.COM_USERNAME and self.COM_ALIAS and self.COM_REALNAME:
		community = users.Entity.get_entity( self.COM_USERNAME )
		if community is None:
			community = users.Community.create_community( username=self.COM_USERNAME )
			com_names = user_interfaces.IFriendlyNamed( community )
			com_names.alias = self.COM_ALIAS
			com_names.realname = self.COM_REALNAME

		user.join_community( community )
		user.follow( community )

@interface.implementer(ISitePolicyUserEventListener)
class MathcountsSitePolicyEventListener(GenericKidSitePolicyEventListener):
	"""
	Implements the policy for the mathcounts site.
	"""

	NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = 'new_user_created_mathcounts'

	IF_ROOT = IMathcountsUser
	IF_WITH_AGREEMENT = IMathcountsCoppaUserWithAgreement
	IF_WOUT_AGREEMENT = IMathcountsCoppaUserWithoutAgreement

	COM_USERNAME = 'MATHCOUNTS'
	COM_ALIAS = 'MATHCOUNTS'
	COM_REALNAME = 'MATHCOUNTS'

	def user_created( self, user, event ):
		"""
		This policy places newly created users in the ``MathCounts`` community
		(creating it if it doesn't exist).

		"""
		super(MathcountsSitePolicyEventListener,self).user_created( user, event )
		_join_community_user_created( self, user, event )


@interface.implementer(ISitePolicyUserEventListener)
class TestMathcountsSitePolicyEventListener(MathcountsSitePolicyEventListener):
	"""
	Implements the policy for the mathcounts site.
	"""

	COM_USERNAME = 'testmathcounts.nextthought.com'
	COM_ALIAS = 'TEST MATHCOUNTS TEST'
	COM_REALNAME = 'TEST MATHCOUNTS TEST'


_SITE_LANDING_PAGES = {
	'mathcounts.nextthought.com': b'tag:nextthought.com,2011-10:mathcounts-HTML-mathcounts2013.warm_up_1',
	'testmathcounts.nextthought.com': b'tag:nextthought.com,2011-10:mathcounts-HTML-testmathcounts2013.warm_up_1',
	'prmia.nextthought.com': b'tag:nextthought.com,2011-10:PRMIA-HTML-Volume_III.A.2_converted.toc260827905'
	}

@component.adapter(nti_interfaces.IUser,app_interfaces.IUserLogonEvent)
def send_site_default_landing_page_cookie( user, event ):
	"""
	This is a hardcoded logon listener to send a cookie to
	tell the app to direct to a specific page at logon time.

	We don't have a good way to direct events through site policies yet
	so we hack it in with a dictionary.
	"""

	for site_name in get_possible_site_names( request=event.request ):
		if site_name in _SITE_LANDING_PAGES:
			event.request.response.set_cookie( b'nti.landing_page',
											   value=urllib.quote( _SITE_LANDING_PAGES[site_name] ) )
			break


@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class NoAvatarUploadCapabilityFilter(object):
	"""
	Removes the ability to upload avatars.
	"""

	def __init__( self, context=None ):
		pass

	def filterCapabilities( self, capabilities ):
		result = set(capabilities)
		result.discard( 'nti.platform.customization.avatar_upload' )
		return result

@interface.implementer(app_interfaces.IUserCapabilityFilter)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class NoChatCapabilityFilter(NoAvatarUploadCapabilityFilter):
	"""
	Removes chat.
	"""

	def __init__( self, context=None ):
		pass

	def filterCapabilities( self, capabilities ):
		result = super(NoChatCapabilityFilter,self).filterCapabilities( capabilities )
		result.discard( 'nti.platform.p2p.chat' )
		return result


@interface.implementer(ISitePolicyUserEventListener)
class _AdultCommunitySitePolicyEventListener(GenericAdultSitePolicyEventListener):
	"""
	Implements the policy for ad adult site, adding new users to a single community.
	"""

	COM_USERNAME = None
	COM_ALIAS = None
	COM_REALNAME = None

	def user_created( self, user, event ):
		"""
		This policy places newly created users in the community defined by the fields
		of this object (creating it if it doesn't exist).

		"""
		super(_AdultCommunitySitePolicyEventListener,self).user_created( user, event )
		_join_community_user_created( self, user, event )


@interface.implementer(ISitePolicyUserEventListener)
class RwandaSitePolicyEventListener(_AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for the rwanda site.
	"""
	COM_USERNAME = 'CarnegieMellonUniversity'
	COM_ALIAS = 'CMU'
	COM_REALNAME = 'Carnegie Mellon University'

@interface.implementer(ISitePolicyUserEventListener)
class LawSitePolicyEventListener(_AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``law.nextthought.com``.
	"""

	COM_USERNAME = 'law.nextthought.com'
	COM_ALIAS = 'Law'
	COM_REALNAME = 'Legal Studies'

@interface.implementer(ISitePolicyUserEventListener)
class PrmiaSitePolicyEventListener(_AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for ``prmia.nextthought.com``.
	"""

	COM_USERNAME = 'prmia.nextthought.com'
	COM_ALIAS = 'PRMIA'
	COM_REALNAME = "Professional Risk Managers' International Association"

@interface.implementer(ISitePolicyUserEventListener)
class LitWorldSitePolicyEventListener(_AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for the litworld site.
	"""

	COM_USERNAME = 'litworld.nextthought.com'
	COM_ALIAS = 'LitWorld'
	COM_REALNAME = 'LitWorld'

@interface.implementer(ISitePolicyUserEventListener)
class CollegiateSitePolicyEventListener(_AdultCommunitySitePolicyEventListener):
	"""
	Implements the policy for the Collegiate site.
	"""

	COM_USERNAME = 'collegiate.nextthought.com'
	COM_ALIAS = 'Collegiate'
	COM_REALNAME = 'Collegiate'
