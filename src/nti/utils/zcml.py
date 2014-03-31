#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML: registering static keys.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import base64
import urllib
import functools

from zope import schema
from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from . import ldap
from . import interfaces as util_interfaces

BASE_64 = u'base64'
URL_QUOTE = u'urlquote'
PASSWORD_ENCODING = (URL_QUOTE, BASE_64)

class IRegisterLDAP(interface.Interface):
	"""
	The arguments needed for registering an ldap
	"""
	id = fields.TextLine(title="ldap identifier", required=True)
	url = fields.TextLine(title="ldap url", required=True)
	username = fields.TextLine(title="Bind username", required=True)
	password = schema.Password(title="Bind password", required=True)
	baseDN = fields.TextLine(title="Base DN", required=False)
	encoding = fields.TextLine(title="Password encoding", required=False)
	backupURL = fields.TextLine(title="ldap backup url", required=False)
	
def registerLDAP(_context, id, url, username, password, baseDN=None, encoding=None,
				 backupURL=None):
	"""
	Register an ldap
	"""
	encoding = encoding or u''
	if encoding.lower() == URL_QUOTE:
		password = urllib.unquote(password)
	elif encoding.lower() == BASE_64:
		password = base64.decodestring(password)

	factory = functools.partial(ldap.LDAP, ID=id, URL=url, Username=username,
								Password=password, BaseDN=baseDN, BackupURL=backupURL)

	utility(_context, provides=util_interfaces.ILDAP, factory=factory, name=id)
