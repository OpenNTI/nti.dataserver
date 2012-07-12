#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface

from . import interfaces

from nti.utils.schema import PermissiveSchemaConfigured as SchemaConfigured
from nti.externalization.externalization import make_repr

# FIXME: Note that we are using the legacy class-based
# functionality to create new internal objects from externals

@interface.implementer( interfaces.IContentRangeDescription )
class ContentRangeDescription(SchemaConfigured):
	"""
	Implementation of :class:`interfaces.IContentRangeDescription`
	"""
	__external_can_create__ = True

	# Including base equality here makes us falsely compare
	# equal to subclasses...it's confusing and screws up tests

	__repr__ = make_repr()


@interface.implementer(interfaces.IDomContentRangeDescription)
class DomContentRangeDescription(ContentRangeDescription):
	"""
	"""
	start = None
	end = None
	ancestor = None

	def __eq__( self, other ):
		try:
			return self is other or (self.start == other.start
									 and self.end == other.end
									 and self.ancestor  == other.ancestor)
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		res = self == other
		if res in (True,False):
			return not res
		return NotImplemented

class ContentPointer(SchemaConfigured):
	__external_can_create__ = True


@interface.implementer( interfaces.IDomContentPointer )
class DomContentPointer(ContentPointer):
	"""
	"""
	role = None
	def __eq__( self, other ):
		try:
			return self is other or self.role == other.role
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		try:
			return self is not other and self.role != other.role
		except AttributeError:
			return NotImplemented

	__repr__ = make_repr()


@interface.implementer(interfaces.IElementDomContentPointer)
class ElementDomContentPointer(DomContentPointer):
	"""
	"""
	elementId = None
	elementTagName = None

	def __eq__( self, other ):
		try:
			return self is other or (self.elementId == other.elementId
									 and self.elementTagName == other.elementTagName
									 and self.role  == other.role)
		except AttributeError:
			return NotImplemented


@interface.implementer(interfaces.ITextContext)
class TextContext(SchemaConfigured):
	"""
	"""
	__external_can_create__ = True

	contextText = ''
	contextOffset = 0

	def __eq__( self, other ):
		try:
			return self is other or (self.contextText == other.contextText
									 and self.contextOffset == other.contextOffset)
		except AttributeError:
			return NotImplemented

	__repr__ = make_repr()


@interface.implementer(interfaces.ITextDomContentPointer)
class TextDomContentPointer(DomContentPointer):
	"""
	"""

	ancestor = None
	contexts = ()
	edgeOffset = 0

	def __eq__( self, other ):
		try:
			return (super(TextDomContentPointer,self).__eq__( other ) is True
					# damn tuples and lists are not ever equal to each other
					# try to compare tuples, keeping in mind the other object may not have one at all
					and tuple(self.contexts) == tuple(other.contexts)
					and self.ancestor == other.ancestor
					and self.edgeOffset == other.edgeOffset )
		except AttributeError:
			return NotImplemented
