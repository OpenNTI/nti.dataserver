#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A tween that begins and ends transactions around its handler. This is initially
very similar to :mod:`pyramid_tm`, but with the following changes:

* The transaction is rolled back if the request is deemed to be
  side-effect free (this has intimate knowledge of the paths that do
  not follow the HTTP rules for a GET being side-effect free; however,
  if you are a GET request and you violate the rules by having
  side-effects, you can set the environment key
  ``nti.request_had_transaction_side_effects`` to ``True``)

* Logging is added to account for the time spent in aborts and commits.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from ZODB.loglevels import TRACE

from pyramid.httpexceptions import HTTPException
from pyramid.httpexceptions import HTTPBadRequest

from nti.transactions.transactions import TransactionLoop

def _commit_veto(request, response):
	"""
	When used as a commit veto, the logic in this function will cause the
	transaction to be aborted if:

	* An ``X-Tm`` response header with the value ``abort`` (or any value
	  other than ``commit``) exists.

	* The response status code starts with ``4`` or ``5``.

	# The request environment has a true value for `nti.commit_veto`

	Otherwise the transaction will be allowed to commit.
	"""
	xtm = response.headers.get('x-tm')
	if xtm is not None:  # pragma: no cover
		return xtm != 'commit'
	if response.status.startswith(('4', '5')):
		return True
	return request.environ.get('nti.commit_veto')

def _is_side_effect_free(request):
	"""
	Is the request side-effect free? If the answer is yes, we should be able to quietly abort
	the transaction and avoid taking out any locks in the DBs.
	"""
	if request.method == 'GET' or request.method == 'HEAD':
		# GET/HEAD requests must NEVER have side effects.
		if 'socket.io' in request.url:
			# (Unfortunately, socket.io polling does)
			# However, the static resources don't
			return True if 'static' in request.url else False
		return True
	# Every non-get probably has side effects
	return False

class _transaction_tween(TransactionLoop):

	def prep_for_retry(self, number, request):
		# make_body_seekable will copy wsgi.input if necessary,
		# otherwise it will rewind the copy to position zero
		try:
			request.make_body_seekable()
		except IOError as e:
			# almost always " unexpected end of file reading request";
			# (though it could also be a tempfile issue if we spool to
			# disk?) at any rate,
			# this is non-recoverable
			logger.log(TRACE, "Failed to make request body seekable",
					   exc_info=True)
			# TODO: Should we do anything with the request.response? Set an error
			# code? It won't make it anywhere...

			# However, it is critical that we return a valid Response
			# object, even if it is an exception response, so that
			# Pyramid doesn't blow up

			raise self.AbortException(HTTPBadRequest(str(e)),
									  "IOError on reading body")

		# XXX: HACK

		# WebTest, browsers, and many of our integration tests by
		# default sets a content type of
		# 'application/x-www-form-urlencoded' If you happen to access
		# request.POST, though, (like locale negotiation does, or
		# certain template operations do) the underlying WebOb will
		# notice the content-type and attempt to decode the body based
		# on that. This leads to a badly corrupted body (if it was
		# JSON) and mysterious failures; this has been seen in the
		# real world. An internal implementation change (accessing
		# POST) suddenly meant that we couldn't read their body.
		# Unfortunately, the mangling is not fully reversible, since
		# it wasn't encoded in the first place.

		# We attempt to fix that here. (This is the best place because
		# we are now sure the body is seekable.)
		if (number == (self.attempts - 1)
			and request.method in ('POST', 'PUT')
			and request.content_type == 'application/x-www-form-urlencoded'):
			body = request.body
			if body and body[0] in (b'{', b'['):
				# encoded data will never start with these values, they would be
				# escaped. so this must be meant to be JSON
				request.content_type = b'application/json'

	def should_abort_due_to_no_side_effects(self, request):
		return	_is_side_effect_free(request) and \
				not request.environ.get('nti.request_had_transaction_side_effects')

	def should_veto_commit(self, response, request):
		return  _commit_veto(request, response) or \
				request.environ.get('nti.early_teardown_happened')  # see zope_site_tween

	def describe_transaction(self, request):
		return None # can turn None

	def run_handler(self, request):
		try:
			return TransactionLoop.run_handler(self, request)  # Not super() for speed
		except HTTPException as e:
			# Pyramid catches these and treats them as a response. We
			# MUST catch them as well and let the normal transaction
			# commit/doom/abort rules take over--if we don't catch
			# them, everything appears to work, but the exception
			# causes the transaction to be aborted, even though the
			# client gets a response.
			#
			# The problem with simply catching exceptions and returning
			# them as responses is that it bypasses pyramid's notion
			# of "exception views". At this writing, we are only
			# using those to turn 403 into 401 when needed, but it
			# can also be used for other things (such as redirecting what
			# would otherwise be a 404).
			# So we wrap up __call__ and also check for HTTPException there
			# and raise it safely after transaction handling is done.
			# Of course, this is only needed if the exception was actually
			# raised, not deliberately returned (commonly HTTPFound and the like
			# are returned)...raising those could have unintended consequences
			request._nti_raised_exception = True
			return e

	def __call__(self, request):
		result = TransactionLoop.__call__(self, request)  # not super() for speed
		if  isinstance(result, HTTPException) and \
			getattr(request, '_nti_raised_exception', False):
			raise result
		return result

def transaction_tween_factory(handler, registry):
	return _transaction_tween(handler)
