#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface

from . import interfaces

@interface.implementer( interfaces.IContentRangeDescription )
class ContentRangeDescription(object):
	"""
	Implementation of IContentRangeDescription.
	"""

def _make_init( cls ):
	def __init__( self, **kwargs ):
		super( cls, self ).__init__()
		for k, v in kwargs:
			if v and hasattr( self, k ):
				setattr( self, k, v )

	return __init__


@interface.implementer(interfaces.IDomContentRangeDescription)
class DomContentRangeDescription(ContentRangeDescription):

	start = None
	end = None
	ancestor = None


DomContentRangeDescription.__init__ = _make_init( DomContentRangeDescription )

class ContentPointer(object):
	pass

@interface.implementer( interfaces.IDomContentPointer )
class DomContentPointer(ContentPointer):

	elementId = None
	elementTagName = None
	type = None

	def __eq__( self, other ):
		return self is other or self.elementId == getattr( other, 'elementId', None ) \
		  and self.elementTagName == getattr( other, 'elementTagName', None ) \
		  and self.type  == getattr( other, 'type', None )

DomContentPointer.__init__ = _make_init( DomContentPointer )

@interface.implementer(interfaces.IElementDomContentPointer)
class ElementDomContentPointer(DomContentPointer):
	pass

@interface.implementer(interfaces.ITextContext)
class TextContext(object):

	contextText = ''
	contextOffset = 0

TextContext.__init__ = _make_init( TextContext )


@interface.implementer(interfaces.ITextDomContentPointer)
class TextDomContentPointer(DomContentPointer):

	contexts = ()
	edgeOffset = 0
