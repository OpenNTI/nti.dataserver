#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
util interfaces

.. $Id: interfaces.py 22564 2013-08-12 11:13:26Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import ValidTextLine

class ILDAP(interface.Interface):
	ID = ValidTextLine(title="LDAP identifier", required=True)
	URL = ValidTextLine(title="LDAP URL", required=True)
	Username = ValidTextLine(title="Bind username", required=True)
	Password = ValidTextLine(title="Bind password flag", required=True)
	BaseDN = ValidTextLine(title="Base DN", required=False)
	BackupURL = ValidTextLine(title="Backup LDAP URL", required=False)

class IOAuthKeys(interface.Interface):
	APIKey = ValidTextLine(title="API Key", required=True)
	SecretKey = ValidTextLine(title="Secret Key", required=True)
