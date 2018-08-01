#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search fragments

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.container.contained import Contained

from nti.contentsearch.interfaces import ISearchFragment

from nti.externalization.representation import WithRepr

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

logger = __import__('logging').getLogger(__name__)


@WithRepr
@interface.implementer(ISearchFragment)
class SearchFragment(SchemaConfigured, Contained):
    createDirectFieldProperties(ISearchFragment)

    mime_type = mimeType = 'application/vnd.nextthought.search.searchfragment'
