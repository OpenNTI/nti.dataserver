#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Patch zope.traversing.api.traverseName and zope.traversing.adapters.DefaultTraverser
to be robust against unicode strings in attr names. Do this
in-place to be sure that even if it's already imported (which is likely) the patches
hold


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface as _zinterface
from zope.traversing import api as _zapi
from zope.traversing import adapters as _zadapters
from zope.traversing import interfaces as _zinterfaces
import sys

# Save the original implementation
_marker = _zadapters._marker
def _nti_traversePathElement( obj, name, further_path, default=_marker,
							  traversable=None, request=None): pass
_nti_traversePathElement.__code__ = _zadapters.traversePathElement.__code__
# Carefully add the right globals. Too much screws things up
_nti_traversePathElement.func_globals['ITraversable'] = _zinterfaces.ITraversable
_nti_traversePathElement.func_globals['LocationError'] = _zinterfaces.TraversalError
_nti_traversePathElement.func_globals['nsParse'] = _zadapters.nsParse
_nti_traversePathElement.func_globals['namespaceLookup'] = _zadapters.namespaceLookup

def _patched_traversePathElement(obj, name, further_path, default=_marker,
								 traversable=None, request=None ):
	try:
		return _nti_traversePathElement(obj, name, further_path, default=default,
										traversable=traversable, request=request)
	except UnicodeEncodeError:
		# Either raise as location error, or return the default
		# The default could have come in either as keyword or positional
		# argument.
		if default is not _marker:
			return default
		# These two things we get from the func_globals dictionary
		info = _nti_exc_info()
		raise LocationError( "Unable to traverse due to attempt to access attribute as unicode.",
							  obj, name ), None, info[2]
_patched_traversing = False
def _patch_traversing():

	@_zinterface.implementer(_zinterfaces.ITraversable)
	class BrokenTraversable(object):
		def traverse( self, name, furtherPath ):
			getattr( self, u'\u2019', None )


	def is_api_broken():
		try:
			_zapi.traverseName( BrokenTraversable(), '' )
		except UnicodeEncodeError:
			return True
		except _zadapters.LocationError:
			return False

	if is_api_broken():
		logger.info( "Monkey patching zope.traversing to be robust to unicode attr names" )

		_zadapters.traversePathElement.__code__ = _patched_traversePathElement.__code__
		_zadapters.traversePathElement.func_globals['_nti_exc_info'] = sys.exc_info
		_zadapters._nti_traversePathElement = _nti_traversePathElement

		global _patched_traversing
		_patched_traversing = True
	assert not is_api_broken(), "Patched it"

	# Now, is the default adapter broken?
	# Note that zope.container.traversal.ContainerTraversable handles this correctly,
	# but it has the order backwards from the DefaultTraversable.
	def is_adapter_broken():
		try:
			_zadapters.DefaultTraversable( object() ).traverse( u'\u2019', () )
		except UnicodeEncodeError:
			return True
		except _zadapters.LocationError:
			return False

	if is_adapter_broken():
		# Sadly, the best thing to do is replace this entirely
		LocationError = _zadapters.LocationError
		def fixed_traverse( self, name, furtherPath ):
			subject = self._subject
			__traceback_info__ = subject, name, furtherPath
			try:
				attr = getattr( subject, name, _marker )
			except UnicodeEncodeError:
				attr = _marker
			if attr is not _marker:
				return attr
			if hasattr(subject, '__getitem__'):
				try:
					return subject[name]
				except (KeyError, TypeError):
					pass
			raise LocationError(subject, name)

		_zadapters.DefaultTraversable.traverse = fixed_traverse
	assert not is_adapter_broken()


_patch_traversing()

del _zinterface
del _zapi
del _zadapters
del _zinterfaces

#del logger

def patch():
	pass
