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
except ImportError:
	import traceback
	traceback.print_exc()
