# Based on code from http://code.activestate.com/recipes/577819-deprecated-decorator/
# Under the MIT license.

import warnings

def deprecated(replacement=None):
	"""A decorator which can be used to mark functions as deprecated.
	replacement is a callable that will be called with the same args
	as the decorated function.

	>>> @deprecated()
	... def foo(x):
	...		return x
	...
	>>> ret = foo(1)
	Warning: foo is deprecated
	>>> ret
	1
	>>>
	>>>
	>>> def newfun(x):
	...		return 0
	...
	>>> @deprecated(newfun)
	... def foo(x):
	...		return x
	...
	>>> ret = foo(1)
	Warning: foo is deprecated; use newfun instead
	>>> ret
	0
	>>>
	"""
	def outer(oldfun):
		def inner(*args, **kwargs):
			msg = "%s is deprecated" % oldfun.__name__
			if replacement is not None:
				msg += "; use %s instead" % (replacement.__name__)
			warnings.warn(msg, FutureWarning, stacklevel=2)
			if replacement is not None:
				return replacement(*args, **kwargs)
			else:
				return oldfun(*args, **kwargs)
		return inner
	return outer
# But use zope.deprecation if available. It's
# more flexible.
try:
	import zope.deprecation
	def deprecated(replacement=None):
		def outer(oldfun):
			msg = "%s is deprecated" % oldfun.__name__
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
		def warn(self, msg, typ, depth ):
			if zope.deprecation.__show__():
				warnings.warn( msg, typ, depth + 1 )

		def __getattr__( self, name ):
			# Let everything else flow through to the real module
			return getattr( warnings, name )

	zope.deprecation.deprecation.__dict__['warnings'] = _warnings()

	class hiding_warnings(object):
		"""
		A context manager that executes its body in a context
		where deprecation warnings are not shown.
		"""
		def __enter__(self):
			zope.deprecation.__show__.off()
		def __exit__( self, *args ):
			zope.deprecation.__show__.on()

except ImportError:
	import traceback
	traceback.print_exc()
