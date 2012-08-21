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

from pyramid.threadlocal import get_current_request

from nti.contentlibrary import interfaces as lib_interfaces
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import shards as nti_shards

def get_possible_site_names():
	"""
	Look for the current request, and return an ordered list
	of site names the request could be considered to be for.
	The list is ordered in preference from most specific to least
	specific. The HTTP origin is considered the most preferred, followed
	by the HTTP Host.

	:return: An ordered sequence of string site names. If there is no request
		or a preferred site cannot be found, returns an empty sequence.
	"""

	request = get_current_request()
	if not request: # pragma: no cover
		return ()

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
	return result

@component.adapter(lib_interfaces.IS3Key)
@interface.implementer(lib_interfaces.IAbsoluteContentUnitHrefMapper)
class RequestAwareS3KeyHrefMapper(object):
	"""
	Produces HTTP URLs for keys in buckets.

	Takes steps to work with CORS and other distribution strategies.
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

	def user_created( user, event ):
		"""
		Called when a user is created.
		"""

from zope.lifecycleevent.interfaces import IObjectCreatedEvent

@component.adapter(nti_interfaces.IUser,IObjectCreatedEvent)
def dispatch_user_created_to_site_policy( user, event ):
	for site_name in get_possible_site_names():
		utility = component.queryUtility( ISitePolicyUserEventListener, name=site_name )
		if utility:
			logger.info( "Site %s wants to handle user creation event with %s", site_name, utility )
			utility.user_created( user, event )
			break

from nti.dataserver import users
import zope.schema
@interface.implementer(ISitePolicyUserEventListener)
class MathcountsSitePolicyEventListener(object):
	"""
	Implements the policy for the mathcounts site.
	"""

	def user_created( self, user, event ):
		"""
		This policy places newly created users in the ``MathCounts`` community
		(creating it if it doesn't exist).

		It also applies the :class:`nti.dataserver.interfaces.ICoppaUserWithoutAgreement` interface
		to the object.

		"""

		community = users.Entity.get_entity( 'MathCounts' )
		if community is None:
			community = users.Community.create_community( username='MathCounts' )


		user.join_community( community )
		user.follow( community )

		interface.alsoProvides( user, nti_interfaces.ICoppaUser )
		interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )

		if user.alias != user.username:
			raise zope.schema.ValidationError("Display name %s and username %s must match." % (user.alias, user.username))

		if any( (x.lower() in user.username.lower() for x in user.realname.split( )) ):
			raise zope.schema.ValidationError("Username %s cannot include any part of the real name %s" %
											 (user.username, user.realname) )

		# TODO: Censor

		if '@' in user.username:
			# This has to go away when those restrictions do
			logger.warning( "Allowing '@' in username for Koppa Kid %s", user )
