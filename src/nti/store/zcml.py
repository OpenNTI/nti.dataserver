#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML: registering static keys.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import schema
from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from .course import create_course
from .purchasable import create_purchasable
from . import interfaces as store_interfaces

class IRegisterPurchasableDirective(interface.Interface):
	"""
	The arguments needed for registering a purchasable item
	"""
	ntiid = fields.TextLine(title="Purchasable item NTIID", required=True)
	title = fields.TextLine(title="Purchasable item title", required=False)
	author = fields.TextLine(title="Purchasable item author", required=False)
	description = fields.TextLine(title="Purchasable item description", required=False,
								  description="If you do not provide, this can come from the body text of the element. Will be interpreted as HTML.")
	amount = schema.Float(title="Cost amount", required=True)
	currency = fields.TextLine(title="Currency amount", required=False, default='USD')
	discountable = fields.Bool(title="Discountable flag", required=False, default=False)
	bulk_purchase = fields.Bool(title="Bulk purchase flag", required=False, default=True)
	icon = fields.TextLine(title='Icon URL', required=False)
	thumbnail = fields.TextLine(title='Thumbnail URL', required=False)
	fee = schema.Float(title="Percentage fee", required=False)
	provider = fields.TextLine(title='Purchasable item provider', required=True)
	license = fields.TextLine(title='Purchasable License', required=False)
	items = fields.Tokens(value_type=schema.TextLine(title='The item identifier'), title="Purchasable content items", required=False)

class IRegisterCourseDirective(IRegisterPurchasableDirective):
	name = schema.TextLine(title="Course name", required=False)
	featured = schema.Bool(title="Featured flag", required=False)
	communities = fields.Tokens(value_type=schema.TextLine(title='The community'), title="Course communities", required=False)
	# overrides
	amount = schema.Float(title="Cost amount", required=False)
	currency = fields.TextLine(title="Currency amount", required=False)
	provider = fields.TextLine(title='Course provider', required=False)
	preview = fields.Bool(title='Preview item flag', required=False)
	
def registerPurchasable(_context, ntiid, provider, title, description=None, amount=None, currency=None,
						items=None, fee=None, author=None, icon=None, thumbnail=None, license=None,
						discountable=False, bulk_purchase=True):
	"""
	Register a purchasable
	"""
	description = _context.info.text.strip() if description is None else description
	factory = functools.partial(create_purchasable, ntiid=ntiid, provider=provider, title=title, author=author,
								description=description, items=items, amount=amount, thumbnail=thumbnail,
								currency=currency, icon=icon, fee=fee, license_=license,
								discountable=discountable, bulk_purchase=bulk_purchase)
	utility(_context, provides=store_interfaces.IPurchasable, factory=factory, name=ntiid)
	logger.debug("Purchasable '%s' has been registered", ntiid)


def registerCourse(_context, ntiid, title, description=None, provider=None, amount=None, currency=None,
				   items=None, fee=None, author=None, icon=None, thumbnail=None, license=None, preview=None,
				   discountable=False, bulk_purchase=False, name=None, communities=None, featured=False):
	"""
	Register a course
	"""
	description = _context.info.text.strip() if description is None else description
	factory = functools.partial(create_course, ntiid=ntiid, provider=provider, title=title, author=author,
								name=name, description=description, items=items, amount=amount,
								currency=currency, icon=icon, fee=fee, license_=license, preview=preview,
								thumbnail=thumbnail, communities=communities, discountable=discountable,
								bulk_purchase=bulk_purchase, featured=featured)
	utility(_context, provides=store_interfaces.ICourse, factory=factory, name=ntiid)
	logger.debug("Course '%s' has been registered", ntiid)

