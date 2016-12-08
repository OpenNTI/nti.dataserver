#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search fragments

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.contained import Contained

from nti.contentsearch.interfaces import ISearchFragment

from nti.externalization.representation import WithRepr

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

@WithRepr
@interface.implementer(ISearchFragment)
class SearchFragment(SchemaConfigured, Contained):
	createDirectFieldProperties(ISearchFragment)
	
	mime_type = mimeType = 'application/vnd.nextthought.search.searchfragment'
