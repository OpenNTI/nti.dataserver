#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebError 0.10.3 has a problem printing the filereporter. When it was lifted from Paste,
it wasn't modified, but the results of format text were modified to return a tuple,
thus it causes a TypeError. (Fixed in an unreleased version: https://github.com/Pylons/weberror/pull/2)

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

try:
	import weberror.reporter
	import weberror.collector
except ImportError:
	# Not installed. Using Paste.exceptions.errormiddleware?
	patched = False
else:
	from cStringIO import StringIO
	import sys

	def _report():
		try:
			raise ValueError()
		except ValueError:
			exc_info = sys.exc_info()

		return weberror.reporter.FileReporter(file=StringIO()).report(weberror.collector.collect_exception(*exc_info))

	try:
		_report()
	except TypeError:
		# Bug!
		class _FileReporter(weberror.reporter.FileReporter):
			def format_text( self, *args, **kwargs ):
				# turn the new tuple into the old plain string
				return super(_FileReporter,self).format_text( *args, **kwargs )[0]
		weberror.reporter.FileReporter = _FileReporter

	_report() # Should now work. If not, something has changed
	patched = True

def patch():
	pass

patch()
