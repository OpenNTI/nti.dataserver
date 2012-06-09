#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from UserDict import DictMixin

from zope import interface


from . import interfaces
from ._util import digester

@interface.implementer(interfaces.IContentUnitRepresentations)
class ContentUnitRepresentations(object,DictMixin):
	"""
	Collects the various representations of a single resource
	together and makes them accessible for querying.

	In effect, this is a convenience for a dictionary using a multi-part key
	with an implicit first part being the resource's ``source`` and the remainder of the parts
	specifying the representation variant.

	..note:: The first part of the representation variant key is required to be one of the
		supported resource types.

	..note:: All parts of the representation variant should be strings or have a reasonable
		string representation
	"""

	def __init__(self, source):
		self.resources = {}
		self.source = source
		self.path = digester.digest(source) # deprecated, to remove

	def has_representation_of_type( self, rep_type_name ):
		"""
		Returns a true value if we have a representation of the given type.
		"""
		return any( (x.resourceType == rep_type_name for x in self.resources.values()) )


	def setResource(self, resource, keys):
		resource.resourceType = keys[0]
		self.resources[digester.digestKeys(keys)] = resource

	def getResource(self, keys):
		if self.hasResource(keys):
			return self.resources[digester.digestKeys(keys)]
		return None

	def hasResource(self, keys):
		return digester.digestKeys(keys) in self.resources

	def keys(self):
		return self.resources.keys()

	__getitem__ = getResource
	__setitem__ = setResource
	__contains__ = hasResource

ResourceRepresentations = ContentUnitRepresentations

@interface.implementer(interfaces.IContentUnitRepresentation)
class ContentUnitRepresentation(object):

	resourceSet = None
	resourceType = None
	source = None
	qualifiers = ()


	def __init__( self, **kwargs ):
		for k, v in kwargs.items():
			if v is not None and hasattr(self, k):
				setattr( self, k, v )


Resource = ContentUnitRepresentation

@interface.implementer(interfaces.IFilesystemContentUnitRepresentation)
class FilesystemContentUnitRepresentation(ContentUnitRepresentation):
	path = None
