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
	def __eq__( self, other ):
		return self is other or isinstance( other, ContentRangeDescription )

	__repr__ = make_repr()


@interface.implementer(interfaces.IDomContentRangeDescription)
class DomContentRangeDescription(ContentRangeDescription):
	"""
	"""
	start = None
	end = None
	ancestor = None

	def __eq__( self, other ):
		return self is other or (self.start == getattr( other, 'start', None )
								 and self.end == getattr( other, 'end', None )
								 and self.ancestor  == getattr( other, 'ancestor', None ))

class ContentPointer(SchemaConfigured):
	__external_can_create__ = True


@interface.implementer( interfaces.IDomContentPointer )
class DomContentPointer(ContentPointer):
	"""
	"""
	role = None
	def __eq__( self, other ):
		return self is other or self.role == getattr( other, 'role', None )

	__repr__ = make_repr()


@interface.implementer(interfaces.IElementDomContentPointer)
class ElementDomContentPointer(DomContentPointer):
	"""
	"""
	elementId = None
	elementTagName = None

	def __eq__( self, other ):
		return self is other or (self.elementId == getattr( other, 'elementId', None )
								 and self.elementTagName == getattr( other, 'elementTagName', None )
								 and self.role  == getattr( other, 'role', None ))


@interface.implementer(interfaces.ITextContext)
class TextContext(SchemaConfigured):
	"""
	"""
	__external_can_create__ = True

	contextText = ''
	contextOffset = 0

	def __eq__( self, other ):
		return self is other or (self.contextText == getattr( other, 'contextText', None )
								 and self.contextOffset == getattr( other, 'contextOffset', None ) )
	__repr__ = make_repr()


@interface.implementer(interfaces.ITextDomContentPointer)
class TextDomContentPointer(DomContentPointer):
	"""
	"""

	ancestor = None
	contexts = ()
	edgeOffset = 0

	def __eq__( self, other ):
		return (super(TextDomContentPointer,self).__eq__( other )
				# damn tuples and lists are not ever equal to each other
				# try to compare tuples, keeping in mind the other object may not have one at all
				and tuple(self.contexts) == tuple(getattr( other, 'contexts', (1,2,3) ))
				and self.ancestor == getattr( other, 'ancestor', None )
				and self.edgeOffset == getattr( other, 'edgeOffset', None ) )
