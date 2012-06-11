#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface

from . import interfaces

from nti.externalization.externalization import make_repr

# FIXME: Note that we are using the legacy class-based
# functionality to create new internal objects from externals

def _make_init( cls ):
	"""
	Returns an init method for cls that takes keyword arguments for the attributes of the
	object. Assumes that the class or instance will have already set up attributes to match
	incoming keyword names.
	"""
	def __init__( self, **kwargs ):
		super( cls, self ).__init__()
		for k, v in kwargs.items():
			if v is not None and hasattr( self, k ):
				setattr( self, k, v )

	return __init__

@interface.implementer( interfaces.IContentRangeDescription )
class ContentRangeDescription(object):
	"""
	Implementation of IContentRangeDescription.
	"""
	__external_can_create__ = True
	def __eq__( self, other ):
		return self is other or isinstance( self, ContentRangeDescription )

ContentRangeDescription.__init__ = _make_init( ContentRangeDescription )
ContentRangeDescription.__repr__ = make_repr()


@interface.implementer(interfaces.IDomContentRangeDescription)
class DomContentRangeDescription(ContentRangeDescription):

	start = None
	end = None
	ancestor = None

	def __eq__( self, other ):
		return self is other or (self.start == getattr( other, 'start', None )
								 and self.end == getattr( other, 'end', None )
								 and self.ancestor  == getattr( other, 'ancestor', None ))

class ContentPointer(object):
	__external_can_create__ = True


@interface.implementer( interfaces.IDomContentPointer )
class DomContentPointer(ContentPointer):

	def __eq__( self, other ):
		return self is other or isinstance( other, DomContentPointer )

DomContentPointer.__init__ = _make_init( DomContentPointer )
DomContentPointer.__repr__ = make_repr()

@interface.implementer(interfaces.IElementDomContentPointer)
class ElementDomContentPointer(DomContentPointer):
	elementId = None
	elementTagName = None
	type = None

	def __eq__( self, other ):
		return self is other or (self.elementId == getattr( other, 'elementId', None )
								 and self.elementTagName == getattr( other, 'elementTagName', None )
								 and self.type  == getattr( other, 'type', None ))


@interface.implementer(interfaces.ITextContext)
class TextContext(object):
	__external_can_create__ = True

	contextText = ''
	contextOffset = 0

	def __eq__( self, other ):
		return self is other or (self.contextText == getattr( other, 'contextText', None )
								 and self.contextOffset == getattr( other, 'contextOffset', None ) )

TextContext.__init__ = _make_init( TextContext )
TextContext.__repr__ = make_repr()


@interface.implementer(interfaces.ITextDomContentPointer)
class TextDomContentPointer(DomContentPointer):

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
