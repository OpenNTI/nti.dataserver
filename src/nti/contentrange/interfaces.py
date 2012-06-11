#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces relating to content ranges.

For a more complete explanation, see content-anchoring.rst.
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import schema

class IContentRangeDescription(interface.Interface):
    """
    Base class for things that define or demarcate a range of content. A
    specific type of content representation will have a specific subclass
    of this interface defining how to refer to content in that representation.
    """


POINTER_TYPE_VOCABULARY = schema.vocabulary.SimpleVocabulary(
	[schema.vocabulary.SimpleTerm( 'start' ),
	 schema.vocabulary.SimpleTerm( 'end' ),
	 schema.vocabulary.SimpleTerm( 'ancestor' )] )

class IDomContentPointer(interface.Interface):
	"""
	Identifies a specific node within an HTML DOM.
	"""

class IElementDomContentPointer(IDomContentPointer):
	"Identifies a specific Element within a DOM."

	elementId = schema.TextLine( title="The ID of an Element in the DOM. Required" )
	elementTagName = schema.TextLine( title="The tagname of an Element in the DOM. Required" )
	type = schema.Choice( title="Intended use of this content pointer.",
						  vocabulary = POINTER_TYPE_VOCABULARY )

class ITextContext(interface.Interface):
	contextText = schema.Text( title="Contextual text." )
	contextOffset = schema.Int( title="Offset from the start or end of the textContent.",
								min=0 )

class ITextDomContentPointer(IDomContentPointer):
	"""
	Identifies a specific point within a Text node that is a
	descendent of an Element in a DOM.
	"""
	ancestor = schema.Object( IElementDomContentPointer,
							  title="Closest referencable element containing the context; should have type==ancestor." )
	contexts = schema.List( title="At least size 1, plus additional contexts.",
							value_type=schema.Object(ITextContext) )

	edgeOffset = schema.Int( title="Offset from the start or end of the textContent.",
							 min=0 )

class IDomContentRangeDescription(IContentRangeDescription):
	"""
	Base class for content ranges based on a document object model.
	"""

	start = schema.Object( IDomContentPointer, title="Beginning of the range" )
	end = schema.Object( IDomContentPointer, title="End of the range" )
	ancestor = schema.Object( IElementDomContentPointer, title="Common ancestor of start and end." )
