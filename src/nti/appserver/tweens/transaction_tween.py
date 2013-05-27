#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A tween that begins and ends transactions around its handler. This is initially
very similar to :mod:`pyramid_tm`, but with the following changes:

* The transaction is rolled back if the request is deemed to be side-effect free
  (this has intimate knowledge of the paths that do not follow the HTTP rules for a GET being side-effect free)

* Logging is added to account for the time spent in aborts and commits.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from nti.utils.transactions import TransactionLoop

def _commit_veto(request, response):
	"""
	When used as a commit veto, the logic in this function will cause the
	transaction to be aborted if:

	* An ``X-Tm`` response header with the value ``abort`` (or any value
	  other than ``commit``) exists.

	* The response status code starts with ``4`` or ``5``.

	Otherwise the transaction will be allowed to commit.
	"""
	xtm = response.headers.get('x-tm')
	if xtm is not None: # pragma: no cover
		return xtm != 'commit'
	return response.status.startswith(('4', '5'))

def _is_side_effect_free( request ):
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

	def prep_for_retry( self, number, request ):
		# make_body_seekable will copy wsgi.input if necessary,
		# otherwise it will rewind the copy to position zero
		try:
			request.make_body_seekable()
		except IOError as e:
			# almost always " unexpected end of file "; at any
			# rate, this is non-recoverable
			raise self.AbortException( str(e), "IOError on reading body" )

	def should_abort_due_to_no_side_effects( self, request ):
		return _is_side_effect_free( request )

	def should_veto_commit( self, response, request ):
		return _commit_veto( request, response ) or request.environ.get( 'nti.early_teardown_happened' ) # see zope_site_tween

	def describe_transaction( self, request ):
		return request.url

def transaction_tween_factory(handler, registry):
	return _transaction_tween( handler )
