#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML: registering static keys.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from . import ldap
from . import interfaces as util_interfaces

class IRegisterLDAP(interface.Interface):
	"""
	The arguments needed for registering an ldap
	"""
	id = fields.TextLine(title="ldap identifier", required=True)
	url = fields.TextLine(title="ldap url", required=True)
	username = fields.TextLine(title="Bind username", required=True)
	password = fields.TextLine(title="Bind password", required=True)
	
def registerLDAP(_context, id, url, username, password):
	"""
	Register an ldap
	"""
	factory = functools.partial(ldap.LDAP, ID=id, URL=url, Username=username, Password=password)
	utility(_context, provides=util_interfaces.ILDAP, factory=factory, name=id)
