#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


from nti.monkey import traversing_patch_on_import
traversing_patch_on_import.patch()
del traversing_patch_on_import


from pyramid.traversal import _join_path_tuple # TODO: Remove the dependency on pyramid at this level

from zope import component
from zope.location import interfaces as loc_interfaces

from nti.dataserver import interfaces as nti_interfaces


def resource_path( res ):
	# This function is somewhat more flexible than pyramids, and
	# also more strict. It requires strings (not None, for example)
	# and bottoming out an at IRoot. This helps us get things right.
	# It is probably also a bit slower.
	__traceback_info__ = res

	# Ask for the parents; we do this instead of getPath() and url_quote
	# to work properly with unicode paths through the magic of pyramid
	parents = loc_interfaces.ILocationInfo( res ).getParents()
	if parents:
		# Take the root off, it's implicit and has a name of None
		parents.pop()

	# Put it in the order pyramid expects, root first
	# (root is added only to the names to avoid prepending)
	parents.reverse()
	parents.append( res )
	# And let pyramid construct the URL, doing proper escaping and
	# also caching.
	names = [''] # Bottom out at the root
	for p in parents:
		names.append( p. __name__ )
	return _join_path_tuple( tuple(names) )


def normal_resource_path( res ):
	"""
	:return: The result of traversing the containers of `res`,
	but normalized by removing double slashes. This is useful
	when elements in the containment hierarchy do not have
	a name; however, it can hide bugs when all elements are expected
	to have names.
	"""
	# If this starts to get complicated, we can take a dependency
	# on the urlnorm library
	result = resource_path( res )
	result = result.replace( '//', '/' )
	# Our LocalSiteManager is sneaking in here, which we don't want...
	#result = result.replace( '%2B%2Betc%2B%2Bsite/', '' )
	return result

def is_valid_resource_path( target ):
	# We really want to check if this is a valid HTTP URL path. How best to do that?
	# Not documented until we figure it out.
	return isinstance( target, basestring ) and  (target.startswith( '/' ) or target.startswith( 'http://' ) or target.startswith( 'https://' ) )


def find_nearest_site(context):
	"""
	Find the nearest :class:`loc_interfaces.ISite` in the lineage of `context`.
	:param context: The object whose lineage to search. If this object happens to be an
		:class:`nti_interfaces.ILink`, then this attempts to take into account
		the target as well.
	:return: The nearest site. Possibly the root site.
	"""
	__traceback_info__ = context, getattr( context, '__parent__', None )

	try:
		loc_info = loc_interfaces.ILocationInfo( context )
	except TypeError:
		# Not adaptable (not located). What about the target?
		try:
			loc_info = loc_interfaces.ILocationInfo( context.target )
			nearest_site = loc_info.getNearestSite()
		except (TypeError,AttributeError):
			# Nothing. Assume the main site/root
			nearest_site = component.getUtility( nti_interfaces.IDataserver ).root
	else:
		# Located. Better be able to get a site, otherwise we have a
		# broken chain.
		try:
			nearest_site = loc_info.getNearestSite()
		except TypeError:
			# Convertible, but not located correctly.
			if not nti_interfaces.ILink.providedBy( context ):
				raise
			nearest_site = component.getUtility( nti_interfaces.IDataserver ).root


	return nearest_site
