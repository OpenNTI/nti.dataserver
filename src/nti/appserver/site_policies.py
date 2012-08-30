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

from zope import component
from zope import interface
from zope import schema

from pyramid.threadlocal import get_current_request

from nti.contentlibrary import interfaces as lib_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.contentfragments import censor

from nti.dataserver import shards as nti_shards

import nameparser
import datetime

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
		host = request.headers['origin'].split( '//' )[1].split( ":" )[0]
		result.append( host.lower() )
	if request.host:
		# Host is a plain name/IP address, and potentially port
		result.append( request.host.split(':')[0].lower() )

	if 'localhost' in result:
		result.remove( 'localhost' )

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
####

class ISitePolicyUserEventListener(interface.Interface):
	"""
	Register instances of these as utilities by the name of the site
	they should apply to.
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

	def user_will_create( user, event ):
		"""
		Called just before a user is created. Do most validation here.
		"""

from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
import zope.schema


def _dispatch_to_policy( user, event, func_name ):
	# Put the empty name/default component on the end of the list of site names
	site_names = list(get_possible_site_names())
	site_names.append( '' )
	for site_name in site_names:
		utility = component.queryUtility( ISitePolicyUserEventListener, name=site_name )
		if utility:
			logger.info( "Site %s wants to handle user creation event with %s", site_name, utility )
			getattr( utility, func_name )( user, event )
			return

	logger.info( "No site in %s wanted to handle user event for %s", site_names, user )


@component.adapter(nti_interfaces.IUser,IObjectCreatedEvent)
def dispatch_user_created_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_created' )

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillUpdateNewEntityEvent)
def dispatch_user_will_update_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_will_update_new' )

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillCreateNewEntityEvent)
def dispatch_user_will_create_to_site_policy( user, event ):
	_dispatch_to_policy( user, event, 'user_will_create' )

def _censor_usernames( user ):
	policy = censor.DefaultCensoredContentPolicy()

	if policy.censor( user.username, user ) != user.username:
		raise zope.schema.ValidationError( "Username contains a censored sequence", 'Username', user.username )

	names = user_interfaces.IFriendlyNamed( user )
	if names.alias: # TODO: What about realname?
		if policy.censor( names.alias, user ) != names.alias:
			raise zope.schema.ValidationError( "alias contains a censored sequence", 'alias', names.alias )

@interface.implementer(ISitePolicyUserEventListener)
class GenericSitePolicyEventListener(object):
	"""
	Implements a generic policy for all sites.
	"""

	def user_will_update_new( self, user, event ):
		pass

	def user_created( self, user, event ):
		pass

	def user_will_create( self, user, event ):
		"""
		This policy verifies naming restraints.

		"""
		_censor_usernames( user )
		if user.username.endswith( '@nextthought.com' ):
			raise zope.schema.ValidationError( "Invalid username", 'Username', user.username )

		# Icky. For some random reason we require everyone to provide their real name,
		# and we force the display name to be derived from it.
		names = user_interfaces.IFriendlyNamed( user )
		human_name = nameparser.HumanName( names.realname ) # Raises BlankHumanName if missing
		if not human_name.first:
			raise zope.schema.ValidationError( "Must provide first name", 'realname', names.realname )
		if not human_name.last:
			raise zope.schema.ValidationError( "Must provide last name", 'realname', names.realname )
		human_name.capitalize()
		names.realname = unicode(human_name)
		names.alias = human_name.first + ' ' + human_name.last[0]

		profile = user_interfaces.ICompleteUserProfile( user )
		if profile.birthdate:
			if profile.birthdate >= datetime.date.today():
				raise zope.schema.ValidationError( "Birthdate must be in the past", 'birthdate', profile.birthdate.isoformat() )

def _is_thirteen_or_more_years_ago( birthdate ):

	today = datetime.date.today()
	thirteen_years_ago = datetime.date.today().replace( year=today.year - 13 )

	return birthdate < thirteen_years_ago

@interface.implementer(ISitePolicyUserEventListener)
class GenericKidSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements the starting policy for the sites with kids.
	"""

	IF_ROOT = nti_interfaces.ICoppaUser
	IF_WITH_AGREEMENT = nti_interfaces.ICoppaUserWithAgreement
	IF_WOUT_AGREEMENT = nti_interfaces.ICoppaUserWithoutAgreement

	def user_will_update_new( self, user, event ):
		"""
		This policy applies the :class:`nti.dataserver.interfaces.ICoppaUserWithoutAgreement` or
		the :class:`nti.dataserver.interfaces.ICoppaUserWithAgreement` interface
		to the object, which drives the available data to store.
		"""

		interface.alsoProvides( user, self.IF_ROOT )
		iface_to_provide = self.IF_WOUT_AGREEMENT

		if 'birthdate' in event.ext_value and _is_thirteen_or_more_years_ago( zope.interface.common.idatetime.IDate( event.ext_value['birthdate'] ) ):
			iface_to_provide = self.IF_WITH_AGREEMENT

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
			raise zope.schema.ValidationError("Username %s cannot include any part of the real name %s" %
											 (user.username, names.realname), 'Username', user.username )

		if '@' in user.username:
			raise zope.schema.ValidationError( "Username cannot contain '@'", 'Username', user.username )

		# This much is handled in the will_update_event
		#profile = user_interfaces.IUserProfile( user )
		#if profile.birthdate and _is_thirteen_or_more_years_ago( profile.birthdate ):
			# If we can show the kid is actually at least 13, then
			# we don't need to get an agreement

		if nti_interfaces.ICoppaUserWithoutAgreement.providedBy( user ):
			# We can only store the first name for little kids
			names.realname = human_name.first


@interface.implementer(ISitePolicyUserEventListener)
class GenericAdultSitePolicyEventListener(GenericSitePolicyEventListener):
	"""
	Implements a generic policy for adult sites.
	"""

	def user_created( self, user, event ):
		super(GenericAdultSitePolicyEventListener,self).user_created( user, event )
		interface.alsoProvides( user, user_interfaces.IImmutableFriendlyNamed )

	def user_will_create( self, user, event ):
		"""
		This policy verifies naming restraints.

		"""
		super(GenericAdultSitePolicyEventListener,self).user_will_create( user, event )

		profile = user_interfaces.ICompleteUserProfile( user )
		if '@' in user.username:
			if not profile.email:
				profile.email = user.username
			elif user.username != profile.email:
				raise zope.schema.ValidationError( "Using an '@' in username means it must match email", 'Username', user.username )

class IMathcountsUser(nti_interfaces.ICoppaUser):
	pass

class IMathcountsCoppaUserWithoutAgreement(IMathcountsUser, nti_interfaces.ICoppaUserWithoutAgreement):
	pass
class IMathcountsCoppaUserWithAgreement(IMathcountsUser, nti_interfaces.ICoppaUserWithAgreement):
	pass

# TODO: Work in progress
class IMathcountsUserProfile(user_interfaces.IEmailRequiredUserProfile):

	role = schema.Choice( title="Your role in the organization",
						  values=("Student", "Teacher", "Coach", "Parent", "Volunteer", "Other"),
						  default="Other")


@interface.implementer(ISitePolicyUserEventListener)
class MathcountsSitePolicyEventListener(GenericKidSitePolicyEventListener):
	"""
	Implements the policy for the mathcounts site.
	"""

	IF_ROOT = IMathcountsUser
	IF_WITH_AGREEMENT = IMathcountsCoppaUserWithAgreement
	IF_WOUT_AGREEMENT = IMathcountsCoppaUserWithoutAgreement

	def user_created( self, user, event ):
		"""
		This policy places newly created users in the ``MathCounts`` community
		(creating it if it doesn't exist).

		"""
		super(MathcountsSitePolicyEventListener,self).user_created( user, event )

		community = users.Entity.get_entity( 'MathCounts' )
		if community is None:
			community = users.Community.create_community( username='MathCounts' )


		user.join_community( community )
		user.follow( community )


@interface.implementer(ISitePolicyUserEventListener)
class RwandaSitePolicyEventListener(GenericAdultSitePolicyEventListener):
	"""
	Implements the policy for the rwanda site.
	"""

	def user_created( self, user, event ):
		"""
		This policy places newly created users in the ``CarnegieMellonUniversity`` community
		(creating it if it doesn't exist).

		"""

		super(RwandaSitePolicyEventListener,self).user_created( user, event )

		community = users.Entity.get_entity( 'CarnegieMellonUniversity' )
		if community is None:
			community = users.Community.create_community( username='CarnegieMellonUniversity' )
			com_names = user_interfaces.IFriendlyNamed( community )
			com_names.alias = 'CMU'
			com_names.realname = 'Carnegie Mellon University'

		user.join_community( community )
		user.follow( community )
