#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monkey-patch for RelStorage 1.5.1 to work correctly wth persistent 4.0.X.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

def _patch_relstorage_for_newer_persistent():
	from persistent.timestamp import pyTimeStamp
	# The independent release of persistent changes repr(TimeStamp) to
	# return an actual repr of its raw data, not the raw data. This
	# is required for py3, but breaks RelStorage 1.5's assumption that
	# the repr of a timestamp is its raw data.
	# A search of the source code reveals this to only be used in relstorage.storage
	# Depending on whether the c extensions are in play, TimeStamp may
	# be a function or a type...if it is a type, we cannot actually
	# get to it reliably by name
	# The fix for this is merged in github master, post 1.5.1
	def _repr(o):
		if isinstance(o, pyTimeStamp) or (type(o).__name__ == 'TimeStamp' and type(o).__module__ == 'persistent'):
			return o.raw()
		return repr(o)
	import relstorage.storage
	relstorage.storage.repr = _repr


_patch_relstorage_for_newer_persistent()

def patch():
	pass
