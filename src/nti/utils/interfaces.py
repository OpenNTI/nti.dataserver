#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
util interfaces

$Id: interfaces.py 22564 2013-08-12 11:13:26Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from . import schema as nti_schema

class ILDAP(interface.Interface):
	ID = nti_schema.ValidTextLine(title="Ldap identifier", required=True)
	URL = nti_schema.ValidTextLine(title="Ldap URL", required=True)
	Username = nti_schema.ValidTextLine(title="Bind username", required=True)
	Password = nti_schema.ValidTextLine(title="Bind password flag", required=True)
	BaseDN = nti_schema.ValidTextLine(title="Base DN", required=False)
