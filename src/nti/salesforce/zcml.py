# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from . import create_app
from . import interfaces as sf_interfaces

class IRegisterApplication(interface.Interface):
	"""
	The arguments needed for registering a salesforce application
	"""
	client_id = fields.TextLine(title="Client ID", required=True)
	client_secret = fields.TextLine(title="Client Secret", required=True)
	app_id = fields.TextLine(title="Application Id", required=False)
	
def registerApplication(_context, client_id, client_secret, app_id=None):
	"""
	Register a salesforce app
	"""
	app_id  = app_id or u''
	factory = functools.partial(create_app, client_id=client_id, client_secret=client_secret)
	utility(_context, provides=sf_interfaces.ISalesforceApplication, factory=factory, name=app_id)
	logger.debug("Salesforce application has been '%s' has been registered", client_id)
