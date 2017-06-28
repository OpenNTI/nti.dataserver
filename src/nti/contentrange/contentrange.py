#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces

from nti.externalization.representation import WithRepr

from nti.schema.schema import PermissiveSchemaConfigured as SchemaConfigured

# FIXME: Note that we are using the legacy class-based
# functionality to create new internal objects from externals


@WithRepr
@interface.implementer(interfaces.IContentRangeDescription)
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


@interface.implementer(interfaces.IDomContentRangeDescription)
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
@interface.implementer(interfaces.IDomContentPointer)
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


@interface.implementer(interfaces.IElementDomContentPointer)
class ElementDomContentPointer(DomContentPointer):

    mime_type = 'application/vnd.nextthought.contentrange.elementdomcontentpointer'

    elementId = None
    elementTagName = None

    def __eq__(self, other):
        try:
            return self is other or (     self.elementId == other.elementId
                                     and self.elementTagName == other.elementTagName
                                     and self.role == other.role)
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash((self.elemendId, self.elementTagName, self.role))


@WithRepr
@interface.implementer(interfaces.ITextContext)
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


@interface.implementer(interfaces.ITextDomContentPointer)
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
