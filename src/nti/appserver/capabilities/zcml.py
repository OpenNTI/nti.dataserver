#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to capabilities.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from .interfaces import ICapability
from .capability import Capability
from zope.security.zcml import IPermissionDirective
from zope.component.zcml import utility

class IRegisterCapabilityDirective(IPermissionDirective):
	"""
	Register a capability.
	"""

def registerCapability(_context, id, title, description=''):
	cap_id = id
	capability = Capability( cap_id, title, description )
	utility(_context, provides=ICapability, component=capability, name=cap_id)
