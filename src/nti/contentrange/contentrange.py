#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.contentrange.interfaces import ITextContext
from nti.contentrange.interfaces import IDomContentPointer
from nti.contentrange.interfaces import ITextDomContentPointer
from nti.contentrange.interfaces import IContentRangeDescription
from nti.contentrange.interfaces import IElementDomContentPointer
from nti.contentrange.interfaces import IDomContentRangeDescription

from nti.externalization.representation import WithRepr

from nti.schema.schema import PermissiveSchemaConfigured as SchemaConfigured

logger = __import__('logging').getLogger(__name__)


@WithRepr
@interface.implementer(IContentRangeDescription)
class ContentRangeDescription(SchemaConfigured):
    """
    Implementation of :class:`interfaces.IContentRangeDescription`
    """
    __external_can_create__ = True

    mime_type = 'application/vnd.nextthought.contentrange.contentrangedescription'

    # Including base equality here with issubclass makes us falsely compare
    # equal to subclasses...it's confusing and screws up tests...
    # so we violate best practices a bit and check equal types directly
    def __eq__(self, other):
        return type(self) is type(other) and type(other) is ContentRangeDescription

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(ContentRangeDescription)


@interface.implementer(IDomContentRangeDescription)
class DomContentRangeDescription(ContentRangeDescription):

    mime_type = 'application/vnd.nextthought.contentrange.domcontentrangedescription'

    end = None
    start = None
    ancestor = None

    def __eq__(self, other):
        try:
            return self is other or (    self.start == other.start
                                     and self.end == other.end
                                     and self.ancestor == other.ancestor)
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        res = self == other
        if res in (True, False):
            return not res
        return NotImplemented

    def __hash__(self):
        return hash((self.start, self.end, self.ancestor))


class ContentPointer(SchemaConfigured):
    __external_can_create__ = True
    mime_type = 'application/vnd.nextthought.contentrange.contentpointer'


@WithRepr
@interface.implementer(IDomContentPointer)
class DomContentPointer(ContentPointer):

    mime_type = 'application/vnd.nextthought.contentrange.domcontentpointer'

    role = None

    def __eq__(self, other):
        try:
            return self is other or self.role == other.role
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        try:
            return self is not other and self.role != other.role
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash((self.role,))


@interface.implementer(IElementDomContentPointer)
class ElementDomContentPointer(DomContentPointer):

    mime_type = 'application/vnd.nextthought.contentrange.elementdomcontentpointer'

    elementId = None
    elementTagName = None

    def __eq__(self, other):
        try:
            return self is other or (    self.elementId == other.elementId
                                     and self.elementTagName == other.elementTagName
                                     and self.role == other.role)
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash((self.elemendId, self.elementTagName, self.role))


@WithRepr
@interface.implementer(ITextContext)
class TextContext(SchemaConfigured):

    __external_can_create__ = True

    mime_type = 'application/vnd.nextthought.contentrange.textcontext'

    contextText = ''
    contextOffset = 0

    def __eq__(self, other):
        try:
            return self is other or (self.contextText == other.contextText
                                     and self.contextOffset == other.contextOffset)
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash((self.contextText, self.contextOffset))


@interface.implementer(ITextDomContentPointer)
class TextDomContentPointer(DomContentPointer):

    mime_type = 'application/vnd.nextthought.contentrange.textdomcontentpointer'

    ancestor = None
    contexts = ()
    edgeOffset = 0

    def __eq__(self, other):
        try:
            return (super(TextDomContentPointer, self).__eq__(other) is True
                    # damn tuples and lists are not ever equal to each other
                    # try to compare tuples, keeping in mind the other
                    # object may not have one at all
                    and tuple(self.contexts) == tuple(other.contexts)
                    and self.ancestor == other.ancestor
                    and self.edgeOffset == other.edgeOffset)
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash((tuple(self.contexts), self.ancestor, self.edgeOffset))
