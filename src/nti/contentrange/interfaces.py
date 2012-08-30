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
from nti.utils import schema as dmschema

class IContentRangeDescription(interface.Interface):
    """
    Base class for things that define or demarcate a range of content. A
    specific type of content representation will have a specific subclass
    of this interface defining how to refer to content in that representation.
    """


POINTER_ROLE_VOCABULARY = schema.vocabulary.SimpleVocabulary(
	[schema.vocabulary.SimpleTerm( 'start' ),
	 schema.vocabulary.SimpleTerm( 'end' ),
	 schema.vocabulary.SimpleTerm( 'ancestor' )] )

class IDomContentPointer(interface.Interface):
	"""
	Identifies a specific node within an HTML DOM.
	"""
	role = schema.Choice( title="Intended use of this content pointer.",
						  vocabulary=POINTER_ROLE_VOCABULARY )

IDomContentPointer['role']._type = unicode


class IElementDomContentPointer(IDomContentPointer):
	"Identifies a specific Element within a DOM."

	elementId = schema.TextLine( title="The ID of an Element in the DOM. Required", min_length=1 )
	elementTagName = schema.TextLine( title="The tagname of an Element in the DOM. Required", min_length=1 )

class ITextContext(interface.Interface):
	contextText = schema.Text( title="Contextual text.", min_length=1 )
	contextOffset = schema.Int( title="Offset from the start or end of the textContent.",
								min=0 )

class ITextDomContentPointer(IDomContentPointer):
	"""
	Identifies a specific point within a Text node that is a
	descendent of an Element in a DOM.
	"""
	ancestor = dmschema.Object( IElementDomContentPointer,
							  title="Closest referencable element containing the context; should have type==ancestor." )
	contexts = schema.List( title="At least size 1, plus additional contexts.",
							min_length=1,
							value_type=schema.Object(ITextContext) )

	edgeOffset = schema.Int( title="Offset from the start or end of the textContent.",
							 min=0 )

class IDomContentRangeDescription(IContentRangeDescription):
	"""
	Base class for content ranges based on a document object model.
	"""

	start = dmschema.Object( IDomContentPointer, title="Beginning of the range" )
	end = dmschema.Object( IDomContentPointer, title="End of the range" )
	ancestor = dmschema.Object( IElementDomContentPointer, title="Common ancestor of start and end." )
