#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.annotation import IAnnotations

from zope.preference.interfaces import IPreferenceGroup

from zope.schema import NativeStringLine

from nti.schema.field import Object

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class IPreferenceAnnotationFactory(interface.Interface):
    """A factory providing the object to be annotated for a preference group and the annotation key
    """

    annotations = Object(IAnnotations,
                         title=u"Annotation object",
                         description=u"The annotation object to be used for this Preference Group.",
                         required=True)

    annotation_key = NativeStringLine(title=u"Annotation key",
                                      description=u"The annotation key for this Preference Group.",
                                      required=True)


class INTIPreferenceGroup(IPreferenceGroup):
    """A generalized preference group derived from zope.preference"""

    __annotation_factory__ = Object(IPreferenceAnnotationFactory,
                                    title=u"Annotation Factory",
                                    description=u"The annotation factory for this preference group.",
                                    required=True)
