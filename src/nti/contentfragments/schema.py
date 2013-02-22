#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helper classes to use content fragments in :mod:`zope.interface`
or :mod:`zope.schema` declarations.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope.schema import Text, TextLine

from nti.utils.schema import Object # For good validation

from nti.contentfragments import interfaces

def _massage_kwargs( self, kwargs ):

	assert self._iface.isOrExtends( interfaces.IUnicodeContentFragment )
	assert self._iface.implementedBy( self._impl )

	# We're imported too early for ZCA to be configured and we can't automatically
	# adapt.
	if 'default' in kwargs and not self._iface.providedBy( kwargs['default'] ):
		kwargs['default'] = self._impl( kwargs['default'] )
	if 'default' not in kwargs and 'defaultFactory' not in kwargs and not kwargs.get('min_length'): # 0/None
		kwargs['defaultFactory'] = self._impl
	return kwargs
class TextUnicodeContentFragment(Object,Text):
	"""
	A :class:`zope.schema.Text` type that also requires the object implement
	an interface descending from :class:`~.IUnicodeContentFragment`.

	Pass the keyword arguments for :class:`zope.schema.Text` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.
	"""

	_iface = interfaces.IUnicodeContentFragment
	_impl = interfaces.UnicodeContentFragment

	def __init__( self, *args, **kwargs ):
		super(TextUnicodeContentFragment,self).__init__( self._iface, *args, **_massage_kwargs(self, kwargs) )


	def fromUnicode( self, string ):
		"""
		We implement :class:`.IFromUnicode` by adapting the given object
		to our text schema.
		"""
		return super(TextUnicodeContentFragment,self).fromUnicode( self.schema( string ) )

class TextLineUnicodeContentFragment(Object,TextLine):
	"""
	A :class:`zope.schema.TextLine` type that also requires the object implement
	an interface descending from :class:`~.IUnicodeContentFragment`.

	Pass the keyword arguments for :class:`zope.schema.TextLine` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.

	If you pass neither a `default` nor `defaultFactory` argument, a `defaultFactory`
	argument will be provided to construct an empty content fragment.
	"""

	_iface = interfaces.IContentFragment
	_impl = interfaces.UnicodeContentFragment

	def __init__( self, *args, **kwargs ):
		super(TextLineUnicodeContentFragment,self).__init__( self._iface, *args, **_massage_kwargs(self, kwargs) )

	def fromUnicode( self, string ):
		"""
		We implement :class:`.IFromUnicode` by adapting the given object
		to our text schema.
		"""
		return super(TextLineUnicodeContentFragment,self).fromUnicode( self.schema( string ) )


class LatexFragmentTextLine(TextLineUnicodeContentFragment):
	"""
	A :class:`~zope.schema.TextLine` that requires content to be in LaTeX format.

	Pass the keyword arguments for :class:`~zope.schema.TextLine` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.

	.. note:: If you provide a ``default`` string that does not already provide :class:`.ILatexContentFragment`,
		one will be created simply by copying; no validation or transformation will occur.
	"""
	_iface = interfaces.ILatexContentFragment
	_impl = interfaces.LatexContentFragment

class PlainTextLine(TextLineUnicodeContentFragment):
	"""
	A :class:`~zope.schema.TextLine` that requires content to be plain text.

	Pass the keyword arguments for :class:`~zope.schema.TextLine` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.

	.. note:: If you provide a ``default`` string that does not already provide :class:`.ILatexContentFragment`,
		one will be created simply by copying; no validation or transformation will occur.
	"""
	_iface = interfaces.IPlainTextContentFragment
	_impl = interfaces.PlainTextContentFragment


class HTMLContentFragment(TextUnicodeContentFragment):
	"""
	A :class:`~zope.schema.Text` type that also requires the object implement
	an interface descending from :class:`.IHTMLContentFragment`.

	Pass the keyword arguments for :class:`zope.schema.Text` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.

	.. note:: If you provide a ``default`` string that does not already provide :class:`.IHTMLContentFragment`,
		one will be created simply by copying; no validation or transformation will occur.

	"""

	_iface = interfaces.IHTMLContentFragment
	_impl = interfaces.HTMLContentFragment

class SanitizedHTMLContentFragment(HTMLContentFragment):
	"""
	A :class:`Text` type that also requires the object implement
	an interface descending from :class:`.ISanitizedHTMLContentFragment`.

	Pass the keyword arguments for :class:`zope.schema.Text` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.

	.. note:: If you provide a ``default`` string that does not already provide :class:`.ISanitizedHTMLContentFragment`,
		one will be created simply by copying; no validation or transformation will occur.

	"""

	_iface = interfaces.ISanitizedHTMLContentFragment
	_impl = interfaces.SanitizedHTMLContentFragment

class PlainText(TextUnicodeContentFragment):
	"""
	A :class:`zope.schema.Text` that requires content to be plain text.

	Pass the keyword arguments for :class:`~zope.schema.Text` to the constructor; the ``schema``
	argument for :class:`~zope.schema.Object` is already handled.

	.. note:: If you provide a ``default`` string that does not already provide :class:`.IPlainTextContentFragment`,
		one will be created simply by copying; no validation or transformation will occur.

	"""
	_iface = interfaces.IPlainTextContentFragment
	_impl = interfaces.PlainTextContentFragment
