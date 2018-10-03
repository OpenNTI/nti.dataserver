#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope.component.zcml import utility

from zope.configuration.config import defineSimpleDirective

from zope.preference.interfaces import IPreferenceGroup

from nti.dataserver.preference.interfaces import INTIPreferenceGroup

from nti.dataserver.preference.preference import NTIPreferenceGroup

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def preferenceGroup(_context,
                    id,
                    annotation_factory,
                    schema=None,
                    title=u'',
                    description=u'',
                    category=False):
    group = NTIPreferenceGroup(id, annotation_factory, schema, title, description, category)
    utility(_context, INTIPreferenceGroup, group, name=id)


def definePreferenceType(_context,
                         name,
                         factory):

    def customPreferenceGroup(_context,
                    id,
                    schema=None,
                    title=u'',
                    description=u'',
                    category=False):

        preferenceGroup(_context,
                        id,
                        factory,
                        schema,
                        title,
                        description,
                        category)

    defineSimpleDirective(_context, name, IPreferenceGroup, customPreferenceGroup)
