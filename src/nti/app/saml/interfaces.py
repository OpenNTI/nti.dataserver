#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

class ISAMLClient(interface.Interface):
	"""
	An object that can act as a basic SAML client for SSO operations.
	Intended to be registered as a global utility
	"""

	def response_for_logging_in(success, error, state=None, passive=False):
		"""
		Returns an HTTPResponse suitable for initiating the SAML login process from
		the requesting browser.  State must be a json encodable value.  
		If the response is requested as passive an authentication check with 
		the idp will be performed but the request will be made in a passive manor (not presenting
		the user with a login prompt).

		On completion of the SAML process the user's browser will be redirected to the provided
		success or error url.  Any state provided to this function will be provided to success or
		error as tbe `RelayState` param.
		"""
		pass

	def process_saml_acs_request(request):
		"""
		Given a request sent to the SAML acs endpoint parse out an identity like object
		that encapsulates the saml assertion information for the user to be returned
		along with the RelayState that was initially provided to response_for_logging_in
		"""
		pass