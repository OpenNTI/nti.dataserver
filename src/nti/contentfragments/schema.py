#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helper classes to use content fragments in :mod:`zope.interface`
or :mod:`zope.schema` declarations.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope.schema import Text, TextLine
from nti.utils.schema import Object

from . import interfaces

class TextUnicodeContentFragment(Object,Text):
	"""
	A :class:`Text` type that also requires the object implement
	an interface descending from :class:`interfaces.IUnicodeContentFragment`.

	Pass the keyword arguments for :class:`Text` to the constructor; the ``schema``
	argument for :class:`Object` is already handled.
	"""

	_iface = interfaces.IUnicodeContentFragment
	_impl = interfaces.UnicodeContentFragment

	def __init__( self, *args, **kwargs ):
		# We're imported too early for ZCA to be configured and we can't automatically
		# adapt.
		if 'default' in kwargs and not self._iface.providedBy( kwargs['default'] ):
			kwargs['default'] = self._impl( kwargs['default'] )
		super(TextUnicodeContentFragment,self).__init__( self._iface, *args, **kwargs )

class TextLineUnicodeContentFragment(Object,TextLine):
	"""
	A :class:`TextLine` type that also requires the object implement
	an interface descending from :class:`interfaces.IUnicodeContentFragment`.

	Pass the keyword arguments for :class:`TextLine` to the constructor; the ``schema``
	argument for :class:`Object` is already handled.
	"""	"""
	"""

	_iface = interfaces.IContentFragment
	_impl = interfaces.UnicodeContentFragment

	def __init__( self, *args, **kwargs ):
		# We're imported too early for ZCA to be configured and we can't automatically
		# adapt.
		if 'default' in kwargs and not self._iface.providedBy( kwargs['default'] ):
			kwargs['default'] = self._impl( kwargs['default'] )
		super(TextLineUnicodeContentFragment,self).__init__( self._iface, *args, **kwargs )


class LatexFragmentTextLine(TextLineUnicodeContentFragment):
	"""
	A TextLine that requires content to be in LaTeX format.
	"""
	_iface = interfaces.ILatexContentFragment
	_impl = interfaces.LatexContentFragment
