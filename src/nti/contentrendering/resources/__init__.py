#!/usr/bin/env python
"""
Defines objects for creating and querying on disk, in various forms, representations
of portions of a document (such as images and math expressions).

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.deprecation import deprecated
import zope.dottedname.resolve as dottedname

from . import interfaces

def _set_default_resource_types(tabular=False):

	def _implement( cls, types ):
		interface.classImplements( cls,
								   interfaces.IRepresentableContentUnit,
								   interfaces.IRepresentationPreferences )
		cls.resourceTypes = types

	if tabular:
		tabularTypes = ('png', 'svg')
		Arrays = dottedname.resolve('plasTeX.Base.Arrays')
		_implement(Arrays.tabular, tabularTypes)
		_implement(Arrays.tabularx, tabularTypes)
		_implement(Arrays.TabularStar, tabularTypes)

	Boxes = dottedname.resolve( 'plasTeX.Base.Boxes' )
	_implement( Boxes.raisebox, ( 'png','svg' ) )

	Math = dottedname.resolve( 'plasTeX.Base.Math' )
	inlineMathTypes = ('mathjax_inline', )
	#displayMathTypes = ('png', 'svg', 'mathjax_display', )

	# inlineMathTypes = ['mathjax_inline', 'png', 'svg']
	displayMathTypes = ('mathjax_display', )
	_implement(Math.math, inlineMathTypes)
	_implement(Math.ensuremath, inlineMathTypes)

	_implement(Math.displaymath, displayMathTypes)
	_implement(Math.EqnarrayStar, displayMathTypes)
	# TODO: What about eqnarry?
	_implement(Math.equation, displayMathTypes)

	from nti.contentrendering.plastexpackages.graphicx import includegraphics
	_implement( includegraphics, ('png',) )

	from plasTeX.Packages import amsmath

	# TODO: Many of these are probably unnecessary as they share
	# common superclasses
	_implement(amsmath.gather, displayMathTypes)
	_implement(amsmath.align, displayMathTypes)
	_implement(amsmath.alignat, displayMathTypes)
	_implement(amsmath.AlignStar, displayMathTypes)
	_implement(amsmath.GatherStar, displayMathTypes)
	_implement(amsmath.AlignatStar, displayMathTypes)
	_implement(amsmath.smallmatrix, displayMathTypes)

	# Make the image class into a resource
	# FIXME: This needs more as Resource evolves
	Image = dottedname.resolve( 'plasTeX.Imagers.Image' )
	Image._url = None
	Image.url = property( lambda self: self._url, lambda self, nv: setattr( self, '_url', nv ) )

	# XXX FIXME If we don't do this, then we can get
	# a module called graphicx reloaded from this package
	# which doesn't inherit our type. Who is doing that?
	import sys
	sys.modules['graphicx'] = sys.modules['nti.contentrendering.plastexpackages.graphicx']

# While import side-effects are usually bad, setting up the default
# resource types is required to make this package actually work, and
# is extremely unlikely to cause any conflicts or difficulty
_set_default_resource_types()

@interface.implementer(interfaces.IContentUnitRepresentation)
class Resource(object):

	def __init__(self, path=None, url=None, resourceSet=None, checksum=None):
		self.url = url
		self.path = path
		self.checksum = checksum
		self.resourceSet = resourceSet

	def __str__(self):
		return '%s' % self.path

from .contentunitrepresentations import ResourceRepresentations
from .contentunitrepresentations import ContentUnitRepresentations

ResourceSet = ResourceRepresentations
deprecated('ResourceSet', 'Prefer the name ResourceRepresentations')
