#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from .alchemy import create_api_key
from .interfaces import IAlchemyAPIKey

class IRegisterAlchemyAPIKeyDirective(interface.Interface):
	"""
	The arguments needed for registering a key
	"""
	name = fields.TextLine(title="The human readable/writable key name", required=False)
	value = fields.TextLine(title="The actual key value. Should not contain spaces", required=True)

def registerAlchemyAPIKey(_context, value, name=u''):
	"""
	Register an alchemy key with the given alias
	"""
	factory = partial(create_api_key, name=name, value=value)
	utility(_context, provides=IAlchemyAPIKey, factory=factory, name=name)
