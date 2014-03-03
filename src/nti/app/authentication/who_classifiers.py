#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component


from repoze.who.interfaces import IRequestClassifier
from repoze.who.interfaces import IChallengeDecider

from pyramid.interfaces import IRequest

from repoze.who.classifiers import default_request_classifier
from pyramid_who.classifiers import forbidden_challenger

#: A request classification that is meant to indicate a browser
#: or browser-like environment being used programattically, i.e.,
#: a web-app request, as opposed to a pure, interactive human user
#: of the browser
CLASS_BROWSER_APP = 'application-browser'

@interface.provider(IRequestClassifier)
def application_request_classifier( environ ):
	"""
	Extends the default classification scheme to try to detect
	requests in which the browser is being used by an application and we don't
	want to generate a native authentication dialog.

	If the request represents an application, then :const:`CLASS_BROWSER_APP`
	is returned, otherwise, the response may be ``browser``.
	"""

	result = default_request_classifier( environ )

	if result == 'browser':
		ua = environ.get('HTTP_USER_AGENT', '').lower()
		# OK, but is it an programmatic browser request where we'd like to
		# change up the auth rules?
		if environ.get( 'HTTP_X_REQUESTED_WITH', '' ).lower() == b'xmlhttprequest':
			# An easy Yes!
			result = CLASS_BROWSER_APP
		elif environ.get('paste.testing') is True:
			result = environ.get('nti.paste.testing.classification', CLASS_BROWSER_APP )
		elif 'python' in ua or 'httpie' in ua:
			result = CLASS_BROWSER_APP
		else:
			# Hmm. Going to have to do some guessing. Sigh.
			# First, we sniff for something that looks like it's sent by
			# a true web browser, like Chrome or Firefox.
			# Then, if there is an Accept value given other than the default that's
			# sent by user agents like, say, NetNewsWire, then it was probably
			# set programatically.
			# NOTE: For the moment we actually also look for things from the iPad
			# (ntifoundation) for BWC, but we soon expect it to set the X-Requested-With
			# header.
			if ('HTTP_REFERER' in environ
				 and ('mozilla' in ua or 'ntifoundation' in ua)
				 and environ.get('HTTP_ACCEPT', '') != '*/*'):
				result = CLASS_BROWSER_APP
	return result

@interface.implementer(IRequestClassifier)
@component.adapter(IRequest)
def application_request_classifier_for_request(request):
	return application_request_classifier



@interface.provider(IChallengeDecider)
def forbidden_or_missing_challenge_decider( environ, status, headers ):
	"""
	We want to offer an auth challenge (e.g., a 401 response) if
	Pyramid thinks we need one (by default, a 403 response) and if we
	have no credentials at all. (If we have credentials, then the
	correct response is a 403, not a challenge.)
	"""
	return 'repoze.who.identity' not in environ and forbidden_challenger( environ, status, headers )
