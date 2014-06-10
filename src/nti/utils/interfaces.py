#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
util interfaces

.. $Id: interfaces.py 22564 2013-08-12 11:13:26Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from . import schema as nti_schema

class ILDAP(interface.Interface):
	ID = nti_schema.ValidTextLine(title="LDAP identifier", required=True)
	URL = nti_schema.ValidTextLine(title="LDAP URL", required=True)
	Username = nti_schema.ValidTextLine(title="Bind username", required=True)
	Password = nti_schema.ValidTextLine(title="Bind password flag", required=True)
	BaseDN = nti_schema.ValidTextLine(title="Base DN", required=False)
	BackupURL = nti_schema.ValidTextLine(title="Backup LDAP URL", required=False)

class IOAuthKeys(interface.Interface):
	APIKey = nti_schema.ValidTextLine(title="API Key", required=True)
	SecretKey = nti_schema.ValidTextLine(title="Secret Key", required=True)

class IAfterTransactionEnd(interface.Interface):
	success = nti_schema.Bool(title="Transaction success")

@interface.implementer(IAfterTransactionEnd)
class AfterTransactionEnd(object):

	def __init__(self, success=True):
		self.success = success
