#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IChallenger

from repoze.who.plugins.basicauth import BasicAuthPlugin

from .who_classifiers import CLASS_BROWSER_APP

class ApplicationBasicAuthPlugin(BasicAuthPlugin):
	"""
	For use when the request is probably an interactive XHR request,
	but credentials are totally invalid. We need to send a 401
	response, but sending the WWW-Authenticate header probably causes
	a browser on the other end to pop-up a dialog box, which is no
	help. Technically, this violates the HTTP spec which requires a
	WWW-Authenticate header on a 401; but it seems safer to elide it
	then to create our own type?

	This must be used in an APIFactory that also uses a
	:func:`nti.app.authentication.who_classifiers.application_request_classifier`
	"""

	classifications = {IChallenger: [CLASS_BROWSER_APP],
					   IIdentifier: [CLASS_BROWSER_APP]}

	def challenge(self, environ, status, app_headers, forget_headers):
		exc = super(ApplicationBasicAuthPlugin,self).challenge( environ, status, app_headers, forget_headers )
		del exc.headers['WWW-Authenticate'] # clear out the WWW-Authenticate header
		return exc

	def forget(self, environ, identity):
		return ()
