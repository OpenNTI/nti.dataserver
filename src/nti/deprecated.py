#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""

from __future__ import print_function, unicode_literals


import warnings
import functools
import zope.deprecation
import zope.deferredimport.deferredmodule

def deprecated(replacement=None): # annotation factory
	def outer(oldfun):
		im_class = getattr( oldfun, 'im_class', None )
		if im_class:
			n = '%s.%s.%s' % (im_class.__module__, im_class.__name__, oldfun.__name__)
		else:
			n = oldfun.__name__

		msg = "%s is deprecated" % n
		if replacement is not None:
			msg += "; use %s instead" % (replacement.__name__)
		#return zope.deprecation.deprecated( oldfun, msg )
		return zope.deprecation.deprecate( msg )(oldfun)
	return outer
zope.deprecation.deprecation.__dict__['DeprecationWarning'] = FutureWarning

# The 'moved' method doesn't pay attention to the 'show' flag, which
# produces annoyances in backwards compatibility and test code. Make it do so.
# The easiest way os to patch the warnings module it uses. Fortunately, it only
# uses one method
class _warnings(object):
	def warn(self, msg, typ, stacklevel=0 ):
		if zope.deprecation.__show__():
			warnings.warn( msg, typ, stacklevel + 1 )

	def __getattr__( self, name ):
		# Let everything else flow through to the real module
		return getattr( warnings, name )

zope.deprecation.deprecation.__dict__['warnings'] = _warnings()

# deferred import has the same problems
zope.deferredimport.deferredmodule.__dict__['DeprecationWarning'] = FutureWarning
zope.deferredimport.deferredmodule.__dict__['warnings'] = _warnings()

# NOTE: There is a substantial problem with zope.deferredimport.deferredmodule/deprecatedFrom
# and the like: it loses access to the module __doc__, which makes Sphinx and the like useless
# For this reason, prefer zope.deprecation.

class hiding_warnings(object):
	"""
	A context manager that executes its body in a context
	where deprecation warnings are not shown.
	"""
	def __enter__(self):
		zope.deprecation.__show__.off()
	def __exit__( self, *args ):
		zope.deprecation.__show__.on()


def hides_warnings(f):
	"""
	A decorator that causes the wrapped function to not show warnings when
	it executes.
	"""
	@functools.wraps(f)
	def inner(*args, **kwargs):
		with hiding_warnings():
			return f(*args,**kwargs)
	return inner
