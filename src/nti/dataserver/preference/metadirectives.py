#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.configuration.fields import GlobalObject

from zope.preference.metadirectives import IPreferenceGroupDirective

from zope.schema import DottedName

from nti.schema.field import TextLine

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class INTIPreferenceGroupDirective(IPreferenceGroupDirective):
    """Register an NTI Preference Group"""

    id = DottedName(
        title=u'ID',
        description=u'Required ID for the preference group used to access the group. The ID should be'
                    u'a valid path in the preferences tree.',
        required=True
    )

    annotation_factory = GlobalObject(title=u"Annotation factory",
                                      description=u"The annotation factory for this preference group.",
                                      required=False
                                      )


class IDefinePreferenceType(interface.Interface):

    directive_name = TextLine(title=u'The name for the generated directive.',
                              required=True)


    annotation_factory = GlobalObject(title=u"Annotation factory",
                                      description=u"The annotation factory for this preference group.",
                                      required=False
                                      )
