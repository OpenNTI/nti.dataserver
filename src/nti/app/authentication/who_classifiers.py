#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from pyramid.interfaces import IRequest

from pyramid_who.classifiers import forbidden_challenger

from repoze.who.classifiers import default_request_classifier

from repoze.who.interfaces import IChallengeDecider
from repoze.who.interfaces import IRequestClassifier

#: A request classification that is meant to indicate a browser
#: or browser-like environment being used programattically, i.e.,
#: a web-app request, as opposed to a pure, interactive human user
#: of the browser
CLASS_BROWSER_APP = 'application-browser'

#: A request classification that's meant to indicate
#: a browser being used interactively.
CLASS_BROWSER = 'browser'

#: A group of classifications that are meant to indicate a browser
#: or browser-like environment being interacted with programatically
APP_CLASSES = (CLASS_BROWSER_APP, )

@interface.provider(IRequestClassifier)
def application_request_classifier(environ):
	"""
	Extends the default classification scheme to try to detect
	requests in which the browser is being used by an application and we don't
	want to generate a native authentication dialog.

	If the request represents an application, then :const:`CLASS_BROWSER_APP`
	is returned, otherwise, the response may be ``browser``.
	"""
	result = default_request_classifier(environ)

	if result == CLASS_BROWSER:
		# Recall that WSGI values are specified as Python's native
		# string type. On Py2, this is a byte string.
		# The HTTP spec says that they should be encoded as ISO-8859-1.
		# Rather than either attempt to decode them, or wrap
		# all our constants in str() calls (to make them native)
		# we instead are careful to use the byte prefix for max speed.
		# We have seen some non-ascii characters in the User-Agent header
		# before, so this matters.
		ua = environ.get('HTTP_USER_AGENT', '').lower()

		# OK, but is it an programmatic browser request where we'd like to
		# change up the auth rules?
		if environ.get('HTTP_X_REQUESTED_WITH', '').lower() == b'xmlhttprequest':
			# An easy Yes!
			result = CLASS_BROWSER_APP
		elif environ.get('paste.testing') is True:
			# From unit tests, we want to behave like an application
			result = environ.get('nti.paste.testing.classification', CLASS_BROWSER_APP)
		elif environ.get('HTTP_X_NTI_CLASSIFICATION') and environ['REMOTE_ADDR'] == b'127.0.0.1':
			# Local overrides for testing
			result = environ.get('HTTP_X_NTI_CLASSIFICATION')

		elif b'python' in ua or b'httpie' in ua:
			# From integration tests ('python requests') or from a command-line
			# tool, we also want to behave like an application (this might change
			# as we need to do more HTML testing)
			result = CLASS_BROWSER_APP
		else:
			# Hmm. Going to have to do some guessing. Sigh.
			# First, we sniff for something that looks like it's sent by
			# a true web browser, like Chrome or Firefox.
			# Then, if there is an Accept value given other than the default that's
			# sent by user agents like, say, NetNewsWire (*/*), then it was probably
			# set programatically. This is slightly complicated by the fact
			# that the defaults vary a bit across browsers; we assume that if they ask
			# for text/html and some other stuff (comma-separated) it's a default browser request.
			# Current versions of Firefox, Chrome and Safari all send a string that looks like
			# that (text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8)
			# NOTE: For the moment we actually also look for things from the iPad
			# (ntifoundation, nextthought) for BWC, but we soon expect it to set the X-Requested-With
			# header.
			accept = environ.get('HTTP_ACCEPT', '')
			if b'ntifoundation' in ua or b'nextthought' in ua:
				# extra special casing for ipad
				result = CLASS_BROWSER_APP
			else:
				if accept == '*/*' or  (b',' in accept and b'text/html' in accept):
					# Assume browser or browser-like
					# If we're following a direct link, like from an email or bookmark,
					# it won't have a referrer
					result = CLASS_BROWSER
				elif 'HTTP_REFERER' in environ and (b'mozilla' in ua):
					result = CLASS_BROWSER_APP
	return result

@interface.implementer(IRequestClassifier)
@component.adapter(IRequest)
def application_request_classifier_for_request(request):
	return application_request_classifier

@interface.provider(IChallengeDecider)
def forbidden_or_missing_challenge_decider(environ, status, headers):
	"""
	We want to offer an auth challenge (e.g., a 401 response) if
	Pyramid thinks we need one (by default, a 403 response) and if we
	have no credentials at all. (If we have credentials, then the
	correct response is a 403, not a challenge.)
	"""
	identity = environ.get('repoze.who.identity')

	return not identity and forbidden_challenger(environ, status, headers)
