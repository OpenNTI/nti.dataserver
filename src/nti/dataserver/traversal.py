#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import traversing_patch_on_import
traversing_patch_on_import.patch()
del traversing_patch_on_import

from zope import component
from zope.location import LocationIterator
from zope.location import interfaces as loc_interfaces

# TODO: Remove the dependency on pyramid at this level
from pyramid.traversal import _join_path_tuple, find_interface as _p_find_interface

from nti.dataserver import interfaces as nti_interfaces

def resource_path( res ):
	# This function is somewhat more flexible than Pyramid's, and
	# also more strict. It requires strings (not None, for example)
	# and bottoms out at an IRoot. This helps us get things right.
	# It is probably also a bit slower.
	_known_parents = [] # TODO: Could probably use a __traceback_supplement__ for this
	__traceback_info__ = res, _known_parents

	# Ask for the parents; we do this instead of getPath() and url_quote
	# to work properly with unicode paths through the magic of pyramid
	loc_info = loc_interfaces.ILocationInfo( res )
	try:
		parents = loc_info.getParents()
	except TypeError: # "Not enough context information to get all parents"
		# This is a programming/design error: some object is not where it should be
		_known_parents.extend( LocationIterator( res ) )
		logger.exception( "Failed to get all parents of %r; known parents: %s", res, _known_parents )
		raise

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
		name = p.__name__
		if name is None:
			raise TypeError("Element in the hierarchy is missing __name__")
		names.append( name )
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
	return 	isinstance(target, basestring) and  (target.startswith('/') or \
			target.startswith('http://') or target.startswith('https://'))

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

def find_interface(resource, interface, strict=True):
	"""
	Given an object, find the first object in its lineage providing the given interface.

	This is similar to :func:`pyramid.traversal.find_interface`, but, as with :func:`resource_path`
	requires the strict adherence to the resource tree, unless ``strict`` is set to ``False``
	"""

	__traceback_info__ = resource, interface

	if not strict:
		return _p_find_interface( resource, interface )

	lineage = loc_interfaces.ILocationInfo( resource ).getParents()
	lineage.insert( 0, resource )
	for item in lineage:
		if interface.providedBy( item ):
			return item


from zope.traversing.namespace import adapter
from zope.traversing.interfaces import IPathAdapter

class adapter_request(adapter):
	"""
	Implementation of the adapter namespace that attempts to pass the
	request along when getting an adapter.
	"""

	def __init__( self, context, request=None ):
		super(adapter_request,self).__init__( context, request )
		self.request = request

	def traverse( self, name, ignored ):
		result = None
		if self.request is not None:
			result = component.queryMultiAdapter(
							(self.context, self.request),
							IPathAdapter,
							name )


		if result is None:
			# Look for the single-adapter. Or raise location error
			result = super(adapter_request,self).traverse( name, ignored )

		# Some sanity checks on the returned object
		__traceback_info__ = result, self.context, result.__parent__, result.__name__
		assert nti_interfaces.IZContained.providedBy( result )
		assert result.__parent__ is not None
		if result.__name__ is None:
			result.__name__ = name
		assert result.__name__ == name

		return result

from zope import interface

from zope.container.traversal import ContainerTraversable as _ContainerTraversable

from zope.traversing.interfaces import ITraversable
from zope.traversing.adapters import DefaultTraversable as _DefaultTraversable

from nti.common.property import alias

@interface.implementer(ITraversable)
class ContainerAdapterTraversable(_ContainerTraversable):
	"""
	A :class:`ITraversable` implementation for containers that also
	automatically looks for named path adapters *if* the container
	has no matching key.

	You may subclass this traversable or register it in ZCML
	directly. It is usable both with and without a request.
	"""

	context = alias('_container')

	def __init__( self, context, request=None ):
		super(ContainerAdapterTraversable,self).__init__(context)
		self.context = context
		self.request = request

	def traverse( self, key, remaining_path ):
		try:
			return super(ContainerAdapterTraversable,self).traverse(key, remaining_path)
		except KeyError:
			# Is there a named path adapter?
			return adapter_request( self.context, self.request ).traverse( key, remaining_path )

@interface.implementer(ITraversable)
class DefaultAdapterTraversable(_DefaultTraversable):
	"""
	A :class:`ITraversable` implementation for ordinary objects that also
	automatically looks for named path adapters *if* the traversal
	found no matching path.

	You may subclass this traversable or register it in ZCML
	directly. It is usable both with and without a request.

	"""

	def __init__( self, context, request=None ):
		super(DefaultAdapterTraversable,self).__init__(context)
		self.context = context
		self.request = request

	def traverse( self, key, remaining_path ):
		try:
			return super(DefaultAdapterTraversable,self).traverse(key, remaining_path)
		except KeyError:
			# Is there a named path adapter?
			return adapter_request( self.context, self.request ).traverse( key, remaining_path )
