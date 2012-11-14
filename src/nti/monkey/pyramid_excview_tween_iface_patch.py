#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A `bug in pyramid <https://github.com/Pylons/pyramid/issues/700>`_ causes exceptions
that occur at certain times in tweens to raise a :class:`KeyError` for ``request_iface``
which prevents the real exception from being seen or debugged. This module
provides a wrapper for the tween factory that corrects this problem in a non-obtrusive
way.

This is fixed in 1.4a4 and subsequent, which is now the requirement.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from pyramid import tweens

if 'IRequest' not in tweens.__dict__:
	# This is the only way I could see to differentiate versions.
	# This is not present in 1.3, and we don't want to do this in 1.4
	raise ImportError("Please run setup.py and update the pyramid dependency.")

def _wrap_handler( handler ):
	@functools.wraps(handler)
	def _handler( request ):
		try:
			return handler(request)
		except Exception:
			if 'request_iface' not in request.__dict__:
				from pyramid.interfaces import IRequest
				request.__dict__['request_iface'] = IRequest
			raise

	return _handler

_orig_tween_factory = tweens.excview_tween_factory

@functools.wraps(_orig_tween_factory)
def _wrapping_tween_factory( handler, registry ):
	return _orig_tween_factory( _wrap_handler( handler ),
								registry )


def patch():
	tweens.excview_tween_factory = _wrapping_tween_factory
