#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content management interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.contentfragments.schema import HTMLContentFragment

from nti.utils import schema as nti_schema

class IContentBundle(interface.Interface):
	NTIID = nti_schema.ValidTextLine(title='Purchasable item NTTID', required=True)
	Title = nti_schema.ValidTextLine(title='Purchasable item title', required=False)
	Author = nti_schema.ValidTextLine(title='Purchasable item author', required=False)
	Description = HTMLContentFragment(title='Purchasable item description', required=False, default='')
	Items = schema.FrozenSet(value_type=nti_schema.ValidTextLine(title='The item identifier'), title="Bundle items")

