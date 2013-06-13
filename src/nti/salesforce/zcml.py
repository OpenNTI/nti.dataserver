# -*- coding: utf-8 -*-
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

from . import interfaces as sf_interfaces

class IRegisterSalesforceApplication(interface.Interface):
	"""
	The arguments needed for registering a salesforce application
	"""
	client_id = fields.TextLine(title="Client ID", required=True)
	client_secret = fields.TextLine(title="Client Secret", required=True)
	security_token = fields.TextLine(title="Security token", required=True)

def registerSalesforceApp(_context, client_id, client_secret, security_token):
	"""
	Register a salesforce app
	"""
	factory = functools.partial(create_app, client_id=client_id, client_secret=client_secret, refresh_token=security_token)
	utility(_context, provides=sf_interfaces.ISalesforceApplication, factory=factory, name=client_id)
	logger.debug("Salesforce application has been '%s' has been registered", client_id)
