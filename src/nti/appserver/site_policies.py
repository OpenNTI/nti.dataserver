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
		result.append( host )
	if request.host:
		# Host is a plain name/IP address, and potentially port
		result.append( request.host.split(':')[0] )
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
