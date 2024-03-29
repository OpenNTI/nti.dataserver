#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 33

from zope.generations.generations import SchemaManager


class _ContentSearchSchemaManager(SchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        super(_ContentSearchSchemaManager, self).__init__(generation=generation,
                                                          minimum_generation=generation,
                                                          package_name='nti.contentsearch.generations')


def evolve(context):
    pass
