#!/usr/bin/env python2.7

from __future__ import unicode_literals

import warnings
import itertools

from zope import interface, schema
from zope.deprecation import deprecated
from zope.mimetype.interfaces import IContentTypeAware, IContentType

from zope.location import ILocation

from zope.container.interfaces import IContainer as IZContainer
from zope.container.interfaces import IContainerNamesContainer as IZContainerNamesContainer
from zope.location.interfaces import IContained as IZContained
from zope.location.location import LocationProxy

from zope.interface.common.mapping import IFullMapping
from zope.interface.common.sequence import ISequence

#pylint: disable=E0213,E0211

class StandardExternalFields(object):

	OID   = 'OID'
	ID    = 'ID'
	NTIID = 'NTIID'
	LAST_MODIFIED = 'Last Modified'
	CREATED_TIME = 'CreatedTime'
	CREATOR = 'Creator'
	CONTAINER_ID = 'ContainerId'
	CLASS = 'Class'
	MIMETYPE = 'MimeType'
	LINKS = 'Links'
	HREF = 'href'


StandardExternalFields.ALL = (lambda : [ v for k,v in StandardExternalFields.__dict__.iteritems() if not k.startswith( '_' ) ])()


class StandardInternalFields(object):
	ID = 'id'
	NTIID = 'ntiid'

	CREATOR = 'creator'
	LAST_MODIFIED = 'lastModified'
	LAST_MODIFIEDU = 'LastModified'
	CREATED_TIME = 'createdTime'
	CONTAINER_ID = 'containerId'


class IExternalObject(interface.Interface):
	"""
	Implemented by, or adapted from, an object that can
	be externalized.
	"""

	__external_oids__ = interface.Attribute(
		"""For objects whose external form includes object references (OIDs),
		this attribute is a list of key paths that should be resolved. The
		values for the key paths may be singleton items or mutable sequences.
		Resolution may involve placing a None value for a key.""")

	__external_resolvers__ = interface.Attribute(
		""" For objects who need to perform arbitrary resolution from external
		forms to internal forms, this attribute is a map from key path to
		a function of three arguments, the dataserver, the parsed object, and the value to resolve.
		It should return the new value. Note that the function here is at most
		a class or static method, not an instance method. """)

	__external_can_create__ = interface.Attribute(
		""" This must be set to true, generally at the class level, for objects
		that can be created by specifying their Class name. """)

	__external_class_name__ = interface.Attribute(
		""" If present, the value is a string that is used for the 'Class' key in the
		external dictionary. If not present, the local name of the object's class is
		used instead. """)

	def toExternalObject():
		""" Optional, see this module's toExternalObject() """

	def updateFromExternalObject( parsed, *args, **kwargs ):
		""" Optional, updates this object using the parsed input
		from the external object form. If the object does not implement
		this method, then if it implements clear() and update() those will be
		used. The arguments are optional context arguments possibly passed. One
		common key is dataserver pointing to a Dataserver."""

class INonExternalizableReplacer(interface.Interface):
	"""
	An adapter object called to make a replacement when
	some object cannot be externalized.
	"""

	def __call__(obj):
		"""
		:return: An externalized object to replace the given object. Possibly the
			given object itself if some higher level will handle it.
		"""

class IExternalObjectDecorator(interface.Interface):
	"""
	Used as a subscription adapter to provide additional information
	to the externalization of an object after it has been externalized
	by the primary implementation of :class:`IExternalObject`. Allows for a separation
	of concerns. These are called in no specific order, and so must
	operate by mutating the external object.
	"""

	def decorateExternalObject( origial, external ):
		"""
		:param original: The object that is being externalized.
			Passed to facilitate using non-classes as decorators.
		:param external: The externalization of that object, produced
			by an implementation of :class:`IExternalObject` or
			default rules.
		:return: Undefined.
		"""

class IExternalMappingDecorator(interface.Interface):
	"""
	Used as a subscription adapter to provide additional information
	to the externalization of an object after it has been externalized
	by the primary implementation of :class:`IExternalObject`. Allows for a separation
	of concerns. These are called in no specific order, and so must
	operate by mutating the external object.
	"""

	def decorateExternalMapping( origial, external ):
		"""
		:param original: The object that is being externalized.
			Passed to facilitate using non-classes as decorators.
		:param external: The externalization of that object, an :class:`ILocatedExternalMapping`, produced
			by an implementation of :class:`IExternalObject` or
			default rules.
		:return: Undefined.
		"""

class IExternalizedObject(interface.Interface):
	"""
	An object that has already been externalized and needs no further
	transformation.
	"""

class ILocatedExternalMapping(IExternalizedObject,ILocation,IFullMapping):
	"""
	The externalization of an object as a dictionary, maintaining its location
	information.
	"""

class ILocatedExternalSequence(IExternalizedObject,ILocation,ISequence):
	"""
	The externalization of an object as a sequence, maintaining its location
	information.
	"""
