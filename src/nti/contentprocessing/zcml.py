#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML: registering static keys.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from . import alchemy_key
from . import interfaces as cp_interfaces

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
	factory = functools.partial(alchemy_key.create_api_key, name=name, value=value)
	utility(_context, provides=cp_interfaces.IAlchemyAPIKey, factory=factory, name=name)
