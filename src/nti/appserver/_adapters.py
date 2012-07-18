#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.traversing.namespace import adapter
from zope.traversing import interfaces as trv_interfaces

import ZODB

from nti.appserver import interfaces as app_interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import datastructures
from nti.externalization import interfaces as ext_interfaces

class EnclosureExternalObject(object):
	interface.implements( ext_interfaces.IExternalObject )
	component.adapts( nti_interfaces.IEnclosedContent )

	def __init__( self, enclosed ):
		self.enclosed = enclosed

	def toExternalObject( self ):
		# TODO: I have no idea how best to do this
		return datastructures.toExternalObject( self.enclosed.data )


class BrokenExternalObject(object):
	"""
	Renders broken object. This is mostly for (legacy) logging purposes, as the general NonExternalizableObject support
	catches these now.

	TODO: Consider removing this. Is the logging worth it? Alternately, should the NonExternalizableObject
	adapter be at the low level externization package or up here?
	"""
	interface.implements( ext_interfaces.IExternalObject )
	component.adapts( ZODB.interfaces.IBroken )

	def __init__( self, broken ):
		self.broken = broken

	def toExternalObject( self ):
		# Broken objects mean there's been a persistence
		# issue. Ok to log it because since its broken, it won't try to call back to us
		logger.debug("Broken object found %s, %s", type(self.broken), self.broken)
		result = { 'Class': 'BrokenObject' }
		return result

## External field updates

@interface.implementer(app_interfaces.IExternalFieldResource)
class _DefaultExternalFieldResource(object):

	def __init__( self, key, obj ):
		self.__name__ = key
		# Initially parent is the object. This may be changed later
		self.__parent__ = obj
		self.resource = obj

@interface.implementer(trv_interfaces.ITraversable)
class _AbstractExternalFieldTraverser(object):
	"""
	Subclasses may also be registered in the ``fields`` namespace
	as traversers for their particular objects to support legacy
	paths as well as new paths.
	"""

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request

	def __getitem__( self, key ):
		raise NotImplementedError()

	def traverse( self, name, further_path ):
		try:
			return self[name]
		except KeyError:
			raise loc_interfaces.LocationError( self.context, name )

@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.IShareableModeledContent)
class SharedWithExternalFieldTraverser(_AbstractExternalFieldTraverser):


	def __getitem__( self, key ):
		if key != 'sharedWith':
			raise KeyError(key)
		return _DefaultExternalFieldResource( key, self.context )


@interface.implementer(app_interfaces.IExternalFieldTraversable)
@component.adapter(nti_interfaces.IUser)
class UserExternalFieldTraverser(_AbstractExternalFieldTraverser):

	def __getitem__( self, key ):
		if key not in ('lastLoginTime', 'password', 'mute_conversation', 'unmute_conversation', 'ignoring', 'accepting', 'NotificationCount'):
			raise KeyError(key)
		return _DefaultExternalFieldResource( key, self.context )


## Attachments/Enclosures

class adapter_request(adapter):
	"""
	Implementation of the adapter namespace that attempts to pass the request along when getting an adapter.
	"""

	def __init__( self, context, request=None ):
		adapter.__init__( self, context, request )
		self.request = request

	def traverse( self, name, ignored ):
		result = None
		if self.request is not None:
			result = component.queryMultiAdapter( (self.context, self.request),
												  trv_interfaces.IPathAdapter,
												  name )

		if result is None:
			# Look for the single-adapter. Or raise location error
			result = adapter.traverse( self, name, ignored )

		if nti_interfaces.IZContained.providedBy( result ) and result.__parent__ is None:
			result.__parent__ = self.context
			result.__name__ = name

		return result

class _resource_adapter_request(adapter_request):
	"""
	Unwraps some of the things done in dataserver_pyramid_views
	when we need to work directly with the model objects.
	"""

	def __init__( self, context, request=None ):
		adapter_request.__init__( self, context.resource, request=request )

@interface.implementer(trv_interfaces.IPathAdapter,trv_interfaces.ITraversable,nti_interfaces.IZContained)
@component.adapter(nti_interfaces.ISimpleEnclosureContainer)
class EnclosureTraversable(object):
	"""
	Intended to be registered as an object in the adapter namespace to
	provide access to attachments. (We implement :class:`zope.traversing.interfaces.IPathAdapter`
	to work with the default ``++adapter`` handler, :class:`zope.traversing.namespaces.adapter`,
	and then we further implement :class:`zope.traversing.interfaces.ITraversable` so we
	can find further resources.)
	"""
	__parent__ = None
	__name__ = None

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request

	def traverse( self, name, further_path ):
		try:
			return self.context.get_enclosure( name )
		except KeyError:
			raise loc_interfaces.LocationError( self.context, name )

from nti.utils import create_gravatar_url

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(nti_interfaces.ISectionInfo)
class _SectionInfoUserLikeDecorator(object):
	"""
	For purposes of the web UI, make SectionInfos, the other things that come back
	from searching, look more like entities.
	"""
	# SectionInfo implements toExternalObject() itself, so the IExternalMappingDecorator
	# is useless
	def __init__( self, context ):
		pass

	def decorateExternalObject( self, original, external ):
		if 'Username' not in external:
			external['Username'] = original.NTIID
		for k in ('realname', 'alias' ):
			if k not in external:
				external[k] = original.Description if original.Description else original.ID
		if 'avatarURL' not in external:
			external['avatarURL'] = create_gravatar_url( original.ID, 'identicon' )
