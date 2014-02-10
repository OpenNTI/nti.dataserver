#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Atom workspace/collection related functionality for content package library.

This also handles external permissioning of entries in the library.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.container.interfaces import IContained

from nti.appserver import interfaces as app_interfaces
from nti.contentlibrary import interfaces as content_interfaces
from nti.externalization import interfaces as ext_interfaces

from pyramid.threadlocal import get_current_request
from nti.appserver.pyramid_authorization import is_readable

from nti.externalization.externalization import to_external_object

from zope.proxy.decorator import ProxyBase

class _PermissionedContentPackageLibrary(ProxyBase):
	"""
	A wrapper around the global library that implements
	permissioning of the available titles for the user (which in
	turn gets better etags; see :class:`.library_views.ContentPackageLibraryCacheController`)
	This is a first-step towards better user-specific libraries.

	.. note:: This currently only uses the request, not the user,
		so no matter how you traverse to it, it will be
		permissioned to the current user, not the user in the path.
	"""

	def __new__(cls, base, request):
		return ProxyBase.__new__( cls, base )

	def __init__( self, base, request ):
		ProxyBase.__init__(self, base)
		self.library = base
		self.request = request
		self._v_contentPackages = None

	@property
	def contentPackages(self):
		if self._v_contentPackages is None:
			def test( content_package ):
				if is_readable( content_package, self.request ):
					return True
				# Nope. What about a top-level child?
				return any( (is_readable(child, self.request) for child in content_package.children) )

			self._v_contentPackages = list(filter(test, self.library.contentPackages))

		return self._v_contentPackages


@interface.implementer(content_interfaces.IContentPackageLibrary)
def _library_for_library(library, request):
	result = _PermissionedContentPackageLibrary(library, request)
	return result

@interface.implementer(content_interfaces.IContentPackageLibrary)
def _library_for_user(user, request):
	global_library = component.getUtility( content_interfaces.IContentPackageLibrary )
	result = component.getMultiAdapter( (global_library, request),
										content_interfaces.IContentPackageLibrary )
	return result

@interface.implementer(app_interfaces.IWorkspace)
def _library_workspace_for_library( library, request ):
	library = component.getMultiAdapter( (library, request),
										 content_interfaces.IContentPackageLibrary )
	ws = LibraryWorkspace(library)
	return ws

@interface.implementer(app_interfaces.IWorkspace)
def _library_workspace_for_user( user, request ):
	library = component.getMultiAdapter( (user,request),
										 content_interfaces.IContentPackageLibrary )
	ws = LibraryWorkspace(library)
	ws.__parent__ = user
	return ws



@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(app_interfaces.IUserService)
def _library_workspace( user_service ):
	request = get_current_request()
	user = user_service.user
	ws = component.queryMultiAdapter( (user, request),
									  app_interfaces.IWorkspace,
									  name='Library' )
	if ws:
		ws.__parent__ = user
		return ws


@interface.implementer(app_interfaces.IWorkspace,
					   IContained)
class LibraryWorkspace(object):

	__parent__ = None

	def __init__( self, lib ):
		self._library = lib

	@property
	def name(self):	return "Library"
	__name__ = name

	@property
	def collections( self ):
		# Right now, we're assuming one collection for the whole library
		adapt = component.getAdapter( self._library, app_interfaces.ICollection )
		adapt.__parent__ = self
		return (adapt,)

	# Traversable
	def __getitem__(self, key):
		# Yes, we traverse to our actual library,
		# not the collection wrapper. It will get
		# converted back to the collection for externalization.
		if key == 'Main':
			return self._library
		raise KeyError(key)
	def __len__(self):
		return 1

@interface.implementer(app_interfaces.ILibraryCollection)
@component.adapter(content_interfaces.IContentPackageLibrary)
class LibraryCollection(object):

	__parent__ = None

	def __init__( self, lib ):
		self._library = lib

	@property
	def library(self): return self._library

	@property
	def name(self): return "Main"
	__name__ = name

	@property
	def accepts(self):
		# Cannot add to library
		return ()

from nti.externalization.interfaces import LocatedExternalDict

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(app_interfaces.ILibraryCollection)
class LibraryCollectionDetailExternalizer(object):
	"""
	Externalizes a Library wrapped as a collection.
	"""

	# TODO: This doesn't do a good job of externalizing it,
	# though. We're skipping all the actual Collection parts

	__slots__ = ('_collection',)

	def __init__(self, collection ):
		self._collection = collection

	def toExternalObject(self, **kwargs):
		library = self._collection.library
		result = LocatedExternalDict( {
			'title': "Library",
			'titles' : [to_external_object(x, **kwargs) for x in library.contentPackages] } )
		result.__name__ = self._collection.__name__
		result.__parent__ = self._collection.__parent__
		return result
