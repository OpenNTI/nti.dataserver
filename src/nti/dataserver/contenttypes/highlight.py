#!/usr/bin/env python
"""
Definitions of highlight objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.dataserver.contenttypes.base import UserContentRoot

from nti.dataserver.contenttypes.selectedrange import SelectedRange
from nti.dataserver.contenttypes.selectedrange import SelectedRangeInternalObjectIO

from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IPresentationPropertyHolder

from nti.externalization.interfaces import IClassObjectFactory

from nti.schema.fieldproperty import createDirectFieldProperties

UserContentRoot = UserContentRoot  # BWC top-level import

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IHighlight)
class Highlight(SelectedRange):
    """
    Implementation of a highlight.
    """
    createDirectFieldProperties(IPresentationPropertyHolder)
    createDirectFieldProperties(IHighlight)

    def __init__(self):
        super(Highlight, self).__init__()


@component.adapter(IHighlight)
class HighlightInternalObjectIO(SelectedRangeInternalObjectIO):

    _ext_primitive_out_ivars_ = {'style'} | SelectedRangeInternalObjectIO._ext_primitive_out_ivars_

    def updateFromExternalObject(self, ext_parsed, *args, **kwargs):
        # Merge any incoming presentation properties with what we have;
        # this allows clients to simply drop things they don't know about
        ext_self = self._ext_self
        if 'presentationProperties' in ext_parsed and ext_self.presentationProperties:
            if ext_parsed['presentationProperties'] != ext_self.presentationProperties:
                props = ext_self.presentationProperties
                props.update(ext_parsed['presentationProperties'])
                ext_parsed['presentationProperties'] = props
        SelectedRangeInternalObjectIO.updateFromExternalObject(self, ext_parsed, *args, **kwargs)


@interface.implementer(IClassObjectFactory)
class HighlightFactory(object):

    description = title = "Highlight factory"

    def __init__(self, *args):
        pass

    def __call__(self, *unused_args, **unused_kw):
        return Highlight()

    def getInterfaces(self):
        return (IHighlight,)
