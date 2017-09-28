#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces relating to content ranges.

For a more complete explanation, see content-anchoring.rst.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from nti.schema.field import Int
from nti.schema.field import List
from nti.schema.field import Text
from nti.schema.field import Choice
from nti.schema.field import Object
from nti.schema.field import TextLine


class IContentRangeDescription(interface.Interface):
    """
    Base class for things that define or demarcate a range of content. A
    specific type of content representation will have a specific subclass
    of this interface defining how to refer to content in that representation.
    """


POINTER_ROLE_VOCABULARY = SimpleVocabulary(
    [SimpleTerm(u'start'),
     SimpleTerm(u'end'),
     SimpleTerm(u'ancestor')])


class IContentPointer(interface.Interface):
    pass


class IDomContentPointer(IContentPointer):
    """
    Identifies a specific node within an HTML DOM.
    """
    role = Choice(title=u"Intended use of this content pointer.",
                  vocabulary=POINTER_ROLE_VOCABULARY)
IDomContentPointer['role']._type = unicode


class IElementDomContentPointer(IDomContentPointer):
    """
    Identifies a specific Element within a DOM.
    """

    elementId = TextLine(title=u"The ID of an Element in the DOM. Required",
                         min_length=1)

    elementTagName = TextLine(title=u"The tagname of an Element in the DOM. Required",
                              min_length=1)


class ITextContext(interface.Interface):

    contextText = Text(title=u"Contextual text.",
                       min_length=1)

    contextOffset = Int(title=u"Offset from the start or end of the textContent.",
                        min=0)


class ITextDomContentPointer(IDomContentPointer):
    """
    Identifies a specific point within a Text node that is a
    descendent of an Element in a DOM.
    """

    ancestor = Object(IElementDomContentPointer,
                      title=u"Closest referencable element containing the context; should have type==ancestor.")

    contexts = List(title=u"At least size 1, plus additional contexts.",
                    min_length=1,
                    value_type=Object(ITextContext))

    edgeOffset = Int(title=u"Offset from the start or end of the textContent.",
                     min=0)


class IDomContentRangeDescription(IContentRangeDescription):
    """
    Base class for content ranges based on a document object model.
    """

    start = Object(IDomContentPointer, title=u"Beginning of the range")

    end = Object(IDomContentPointer, title=u"End of the range")

    ancestor = Object(IElementDomContentPointer,
                      title=u"Common ancestor of start and end.")


TIMECONTENT_ROLE_VOCABULARY = SimpleVocabulary(
    [SimpleTerm(u'start'),
     SimpleTerm(u'end')])


class ITimeContentPointer(interface.Interface):

    role = Choice(title=u"Intended use of this time content pointer.",
                  vocabulary=TIMECONTENT_ROLE_VOCABULARY)

    seconds = Int(title=u"Number of seconds from the start of the timeline that this pointer points",
                  min=0)
ITimeContentPointer['role']._type = unicode


class ITimeRangeDescription(IContentRangeDescription):
    """
    Base class for timeline annotations
    """
    seriesId = TextLine(title=u"The id of the timeline this range is within",
                        required=True)

    start = Object(ITimeContentPointer,
                   title=u"Timeline start",
                   required=True)

    end = Object(ITimeContentPointer,
                 title=u"Timeline end",
                 required=False)


class ITranscriptContentPointer(ITimeContentPointer):

    pointer = Object(IDomContentPointer,
                     title=u"Tthe pointer in this cue that defines the edge "
                     u"(start or end based on the value of role) for this edge of the range",
                     required=True)

    cueid = TextLine(title=u"Cue id", required=False)


class ITranscriptRangeDescription(ITimeRangeDescription):

    start = Object(ITranscriptContentPointer,
                   title=u"Transcript pointer start",
                   required=True)

    end = Object(ITranscriptContentPointer,
                 title=u"Transcript pointer end",
                 required=True)
