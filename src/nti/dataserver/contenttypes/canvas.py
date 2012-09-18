#!/usr/bin/env python
"""
Implementations of canvas types.
"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )

import persistent
from persistent.list import PersistentList

import numbers
import six
from urllib import quote as urlquote


from nti.externalization.interfaces import IExternalObject
from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.externalization.interfaces import LocatedExternalDict
#from nti.externalization.externalization import to_external_object
from nti.externalization.oids import to_external_ntiid_oid

from nti.dataserver import mimetype
from nti.dataserver import interfaces as nti_interfaces

from nti.contentfragments import interfaces as frg_interfaces


from zope import interface
from zope import component
from zope.container.contained import contained
import zope.schema.interfaces


from .threadable import ThreadableExternalizableMixin
from .base import UserContentRoot, _make_getitem

#####
# Whiteboard shapes
#####
@interface.implementer(nti_interfaces.ICanvas,nti_interfaces.IZContained)
class Canvas(ThreadableExternalizableMixin, UserContentRoot, ExternalizableInstanceDict):

	# TODO: We're not trying to resolve any incoming external
	# things. Figure out how we want to do incremental changes
	# (pushing new shapes while drawing). Should we take the whole thing every
	# time (and then look for equal object that we already have)? Accept POSTS
	# of shapes into this object as a "container"? Right now, we have disabled
	# persistence of individual shapes so it doesn't do us much good
	__parent__ = None
	__name__ = None

	# We write shapes ourself for speed. The list is often long and only
	# contains _CanvasShape "objects". Note that this means they cannot be decorated
	_excluded_out_ivars_ = ExternalizableInstanceDict._excluded_out_ivars_.union( {'shapeList'} )


	def __init__(self):
		super(Canvas,self).__init__()
		self.shapeList = PersistentList()

	def append( self, shape ):
		if not isinstance( shape, _CanvasShape ):
			__traceback_info__ = shape
			raise zope.schema.interfaces.WrongContainedType()
		self.shapeList.append( shape )
		contained( shape, self, unicode(len(self.shapeList) - 1) )

	__getitem__ = _make_getitem( 'shapeList' )

	def updateFromExternalObject( self, *args, **kwargs ):
		# Special handling of shapeList to preserve the PersistentList.
		# (Though this probably doesn't matter. See the note at the top of the class)
		shapeList = args[0].pop( 'shapeList', self )
		super(Canvas,self).updateFromExternalObject( *args, **kwargs )
		if shapeList is not self:
			# Copy the current files. If we find anything that refers
			# to them as a URL below, swap in the file data and swap out
			# the URL string
			# This is tightly couple to the implementation of CanvasUrlShape
			existing_files = [getattr(x, '_file') for x in self.shapeList if getattr(x, '_file', None )]
			existing_files = {urlquote(to_external_ntiid_oid(x)): x for x in existing_files}
			del self.shapeList[:]
			if shapeList:
				for shape in shapeList:
					self.append( shape )
					if 'url' in shape.__dict__:
						url = shape.__dict__['url']
						for existing_file_url, existing_file in existing_files.items():
							if existing_file_url in url:
								shape.__dict__['url'] = None
								shape.__dict__['_file'] = existing_file
								existing_file.__parent__ = shape

		args[0]['shapeList'] = list(self.shapeList) # be polite and put it back

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(Canvas,self).toExternalDictionary( mergeFrom=mergeFrom )
		result['shapeList'] = [x.toExternalObject() for x in self.shapeList]
		return result

	def __eq__( self, other ):
		# TODO: Super properties?
		try:
			return self.shapeList == other.shapeList
		except AttributeError: #pragma: no cover
			return NotImplemented

@interface.implementer(IExternalObject)
class CanvasAffineTransform(object):
	"""
	Represents the 6 values required in an 2-D affine transform:
	\|a  b  0|
	\|c  d  0|
	\|tx ty 1|

	Treated are like structs, compared by value, not identity. They are
	never standalone, so many of their external fields are lacking. They handle
	all their own externalization and are not meant to be subclassed.
	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	__external_can_create__ = True

	__slots__ = ('a', 'b', 'c', 'd', 'tx', 'ty')

	A = D = 1
	B = C = TX = TY = 0

	def __init__( self ):
		"""
		Initializes to the identity transform.
		"""
		# cannot mix __slots__ with class attributes
		self.a = self.d = self.A
		self.b = self.c = self.tx = self.ty = self.B

	def updateFromExternalObject( self, parsed, **kwargs ):
		for k in self.__slots__:
			if k in parsed:
				val = parsed[k]
				__traceback_info__ = k, val
				assert isinstance( val, numbers.Number )
				setattr( self, k, val )

	def toExternalDictionary( self, mergeFrom=None ):
		"""
		Note that we externalize ourself directly, without going through the superclass
		at all, for speed. We would only delete most of the stuff it added anyway.
		"""
		result = LocatedExternalDict(a=self.a, b=self.b, c=self.c, d=self.d, tx=self.tx, ty=self.ty,
									 Class=self.__class__.__name__, MimeType=self.mime_type)
		return result

	def toExternalObject( self ):
		return self.toExternalDictionary()

	def __eq__( self, other ):
		try:
			return all( [getattr(self, x) == getattr(other,x) for x in self.__slots__] )
		except AttributeError: #pragma: no cover
			return NotImplemented

@interface.implementer(IExternalObject,nti_interfaces.IZContained)
class _CanvasShape(ExternalizableInstanceDict):

	__parent__ = None
	__name__ = None
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	# We generate the affine transform on demand; we don't store it
	# to avoid object overhead.

	_a = _d = CanvasAffineTransform.A
	_b = _c = _tx = _ty = CanvasAffineTransform.TY

	def __init__( self ):
		super(_CanvasShape,self).__init__( )

		# We expose stroke and fill properties optimized
		# for both Web and iPad. The iPad format is a superset
		# of the other format and so that's what we store
		self._stroke_rgba = [1.0, 1.0, 1.0, 1.0]
		self._fill_rgba = [1.0, 1.0, 1.0, 0.0]
		# stroke width is the same both places, and stored in pts.
		self._stroke_width = 1.0

	def get_transform( self ):
		result = CanvasAffineTransform( )
		for x in result.__slots__:
			val = getattr( self, '_' + x )
			if val != getattr( result, x ):
				setattr( result, x, val )
		return result
	def set_transform( self, matrix ):
		__traceback_info__ = matrix
		assert isinstance( matrix, CanvasAffineTransform )
		for x in matrix.__slots__:
			val = getattr( matrix, x )
			if val != getattr( self, '_' + x ):
				setattr( self, '_' + x, val )

	transform = property( get_transform, set_transform )

	def _write_rgba( self, prop_name ):
		val = getattr( self, prop_name )
		if val[3] == 1.0: # Comparing with a constant
			fs = "{:.3f} {:.3f} {:.3f}"
			val = val[0:3]
		else:
			fs = "{:.3f} {:.3f} {:.3f} {:.2f}"
		return fs.format( *val )

	@property
	def strokeRGBAColor(self):
		return self._write_rgba( '_stroke_rgba' )
	@property
	def fillRGBAColor(self):
		return self._write_rgba( '_fill_rgba' )
	@property
	def strokeColor(self):
		return "rgb({:.1f},{:.1f},{:.1f})".format( *[x * 255.0 for x in self._stroke_rgba[0:3]] )
	@property
	def strokeOpacity(self):
		return self._stroke_rgba[3]
	@property
	def strokeWidth(self):
		return "{:.3%}".format( self._stroke_width / 100 )
	@property
	def fillColor(self):
		return "rgb({:.1f},{:.1f},{:.1f})".format( *[x * 255.0 for x in self._fill_rgba[0:3]] )
	@property
	def fillOpacity(self):
		return self._fill_rgba[3]

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(_CanvasShape,self).updateFromExternalObject( parsed, *args, **kwargs )
		# The matrix, if given, convert to our points
		matrix = parsed.pop( 'transform', None )
		if matrix: self.transform = matrix

		# If stroke/fill rgba are given, they take precedence.
		stroke_rgba_string = parsed.pop( 'strokeRGBAColor', None )
		fill_rgba_string = parsed.pop( 'fillRGBAColor', None )

		def update_from_rgb_opacity( arr, colName, opacName ):
			stroke_color = parsed.pop( colName, None )    # "rgb(r,g,b)"
			stroke_opacity = parsed.pop( opacName, None ) # float
			if stroke_color:
				try:
					r, g, b = map( float, stroke_color.strip()[4:-1].split( ',' ) )
				except ValueError:
					logger.warn( "Bad data for %s: %s", colName, stroke_color )
				else:
					assert( 0.0 <= r <= 255.0 )
					assert( 0.0 <= g <= 255.0 )
					assert( 0.0 <= b <= 255.0 )
					arr[0], arr[1], arr[2] = r / 255.0, g / 255.0, b / 255.0
					self._p_changed = True
			if stroke_opacity is not None:
				stroke_opacity = float(stroke_opacity) # accept either string or float
				assert( 0.0 <= stroke_opacity <= 1.0 )
				# opacity and alpha are exactly the same,
				# 0.0 fully transparent, 1.0 fully opaque
				arr[3] = stroke_opacity
				if hasattr( self, '_p_changed'): setattr( self, '_p_changed', True )

		def update_from_rgba( arr, string, alpha=1.0 ):
			"""
			A missing alpha value is assumed to mean 1.0, matching what happens
			with Omni's OQColor.
			"""
			string = string.strip()
			string = string.lower()
			if string.startswith( 'rgba(' ):
				logger.warn( "Bad data for RGBA: %s", string )
				string = string.strip()[5:-1].split( ',' )
				string = ' '.join( string )
			rgba = string.split( ' ' )
			if len(rgba) == 3: rgba = list(rgba); rgba.append( alpha )
			r, g, b, a = map( float, rgba )
			assert( 0.0 <= r <= 1.0 )
			assert( 0.0 <= g <= 1.0 )
			assert( 0.0 <= b <= 1.0 )
			arr[0], arr[1], arr[2] = r, g, b
			assert( 0.0 <= a <= 1.0 )
			arr[3] = a
			if hasattr( self, '_p_changed'): setattr( self, '_p_changed', True )

		if stroke_rgba_string is not None:
			update_from_rgba( self._stroke_rgba, stroke_rgba_string )
		else:
			update_from_rgb_opacity( self._stroke_rgba, 'strokeColor', 'strokeOpacity' )
		if fill_rgba_string is not None:
			update_from_rgba( self._fill_rgba, fill_rgba_string )
		else:
			update_from_rgb_opacity( self._fill_rgba, 'fillColor', 'fillOpacity' )

		stroke_width = parsed.pop( 'strokeWidth', None )
		if stroke_width is not None: # maybe string or float
			if  isinstance( stroke_width, six.string_types ):
				if stroke_width.endswith( '%' ):
					stroke_width = stroke_width[0:-1]
				# Basic b/w compat
				elif stroke_width.endswith( 'pt' ):
					stroke_width = stroke_width[0:-2]
			stroke_width = float(stroke_width)
			assert( stroke_width >= 0.0 )
			assert( stroke_width <= 100.0 )
			self._stroke_width = stroke_width

	def toExternalDictionary( self, mergeFrom=None ):
		# Implementation note: For now, because we are not
		# doing anything fancy with keeping track of identical objects
		# when we update a canvas, we are also eliding these same fields like Point.
		mergeFrom = mergeFrom or {}
		# Avoid the creation of a temporary object and externalize directly
		mergeFrom['transform'] = LocatedExternalDict(a=self._a, b=self._b, c=self._c, d=self._d,
													 tx=self._tx, ty=self._ty,
													 Class=CanvasAffineTransform.__name__, MimeType=CanvasAffineTransform.mime_type)
		#self.transform.toExternalDictionary()

		mergeFrom['strokeRGBAColor'] = self.strokeRGBAColor
		mergeFrom['fillRGBAColor'] = self.fillRGBAColor

		mergeFrom['strokeColor'] = self.strokeColor
		mergeFrom['strokeOpacity'] = self.strokeOpacity
		mergeFrom['strokeWidth'] = self.strokeWidth

		mergeFrom['fillColor'] = self.fillColor
		mergeFrom['fillOpacity'] = self.fillOpacity

		return super(_CanvasShape,self).toExternalDictionary( mergeFrom=mergeFrom )
	__external_use_minimal_base__ = True # Avoid the call to standard_dictionary, and just use the minimal fields

	def toExternalObject( self ):
		return self.toExternalDictionary()

	def __eq__( self, other ):
		# Implementation note: when toExternalDictionary changes,
		# this method should change too
		# TODO: This is a lousy comparison
		try:
			return self.transform == other.transform
		except AttributeError:
			return NotImplemented

class _CanvasCircleShape(_CanvasShape):
	pass
class _CanvasPolygonShape(_CanvasShape):

	_ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union( {'sides'} )


	def __init__(self, sides=4 ):
		super(_CanvasPolygonShape,self).__init__()
		self.sides = sides

	def updateFromExternalObject( self, *args, **kwargs ):
		super(_CanvasPolygonShape,self).updateFromExternalObject( *args, **kwargs )
		assert isinstance( self.sides, numbers.Integral )

	def __eq__( self, other ):
		try:
			return super(_CanvasPolygonShape,self).__eq__( other ) and self.sides == other.sides
		except AttributeError:
			return NotImplemented

class _CanvasTextShape(_CanvasShape):

	_ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union( {'text'} )


	def __init__( self, text='' ):
		super(_CanvasTextShape, self).__init__( )
		self.text = text

	def updateFromExternalObject( self, *args, **kwargs ):
		tbf = self.text
		super(_CanvasTextShape,self).updateFromExternalObject( *args, **kwargs )
		assert isinstance( self.text, six.string_types )
		if self.text != tbf:
			self.text = component.getAdapter( self.text, frg_interfaces.IUnicodeContentFragment, name='text' )

from nti.zodb import urlproperty
from nti.dataserver import links

class _CanvasUrlShape(_CanvasShape):

	# We take responsibility for writing the URL ourself
	_excluded_out_ivars_ = _CanvasShape._excluded_out_ivars_.union( {'url'} )
	_ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union( {'url'} )

	_file = None

	_DATA_NAME = 'data'

	def __init__( self, url='' ):
		super(_CanvasUrlShape, self).__init__( )
		self.url = url

	def updateFromExternalObject( self, *args, **kwargs ):
		super(_CanvasUrlShape,self).updateFromExternalObject( *args, **kwargs )


	url = urlproperty.UrlProperty( data_name=_DATA_NAME, url_attr_name='url', file_attr_name='_file',
								   use_dict=True)

	__getitem__ = url.make_getitem()

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(_CanvasUrlShape,self).toExternalDictionary( mergeFrom=mergeFrom )
		if self._file is not None:
			# See __getitem__
			# TODO: This is pretty tightly coupled to the app layer
			# TODO: If we wanted to be clever, we would have a cutoff point based on the size
			# to determine when to return a link vs the data URL.

			# We do not want to rely on traversal to this object, so we give the exact
			# path to the file. (Traversal works for pure canvas, and canvas-in-note, but breaks
			# for canvas-in-chat-message)
			target = to_external_ntiid_oid( self._file, add_to_connection=True )

			link = links.Link( target=target, target_mime_type=self._file.mimeType, elements=('@@view',), rel="data" )
			interface.alsoProvides( link, nti_interfaces.ILinkExternalHrefOnly )
			result['url'] = link
		else:
			result['url'] = self.url
		return result

	def __repr__(self):
		return '<%s>' % self.__class__.__name__

class _CanvasPathShape(_CanvasShape):

	# We write points ourself for speed. The list is often long and only
	# contains primitives.
	_excluded_out_ivars_ = _CanvasShape._excluded_out_ivars_.union( {'points'} )

	_ext_primitive_out_ivars_ = _CanvasShape._ext_primitive_out_ivars_.union( {'closed'} )

	def __init__( self, closed=True, points=() ):
		super(_CanvasPathShape,self).__init__()
		self.closed = closed
		self.points = points

	def updateFromExternalObject(self, *args, **kwargs ):
		super(_CanvasPathShape,self).updateFromExternalObject( *args, **kwargs )
		assert (isinstance( self.closed, bool ) or self.closed == 0 or self.closed == 1)
		if self.closed == 0 or self.closed == 1:
			self.closed = bool(self.closed)
		for i in self.points:
			assert isinstance( i, numbers.Real )
		assert (len(self.points) % 2) == 0 # Must be even number of pairs

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(_CanvasPathShape,self).toExternalDictionary( mergeFrom=mergeFrom )
		result['points'] = self.points
		return result

	def __eq__( self, other ):
		try:
			return super(_CanvasPathShape,self).__eq__( other ) \
			  and self.closed == other.closed \
			  and self.points == other.points
		except AttributeError:
			return NotImplemented

### Ok, so earlier we screwed up. We had CanvasShape by default
# be persistent. We need the class with that name to continue to be persistent,
# otherwise we cannot load them out of the database. But we want new objects
# to not be persistent, hence the class layout that has non-externally-creatable
# objects at the root, then a persistent subclass that's also not creatable,
# and then a non-persistent subclass that is creatable, but registered
# under all the old names and indistinguishable from outside.
# A migration has moved all old objects to the new version;
# now we need to deprecate the old version and be sure that they don't
# get loaded anymore, then we can delete the class
class CanvasShape(_CanvasShape,persistent.Persistent): pass
class CanvasCircleShape(_CanvasCircleShape,persistent.Persistent): pass
class CanvasPolygonShape(_CanvasPolygonShape,persistent.Persistent): pass
class CanvasTextShape(_CanvasTextShape,persistent.Persistent): pass
class CanvasUrlShape(_CanvasUrlShape,persistent.Persistent): pass
class CanvasPathShape(_CanvasPathShape,persistent.Persistent): pass

class NonpersistentCanvasShape(_CanvasShape):
	__external_can_create__ = True
	mime_type = CanvasShape.mime_type
	__external_class_name__ = 'CanvasShape'


class NonpersistentCanvasCircleShape(_CanvasCircleShape):
	__external_can_create__ = True
	mime_type = CanvasCircleShape.mime_type
	__external_class_name__ = 'CanvasCircleShape'

class NonpersistentCanvasPolygonShape(_CanvasPolygonShape):
	__external_can_create__ = True
	mime_type = CanvasPolygonShape.mime_type
	__external_class_name__ = 'CanvasPolygonShape'

class NonpersistentCanvasTextShape(_CanvasTextShape):
	__external_can_create__ = True
	mime_type = CanvasTextShape.mime_type
	__external_class_name__ = 'CanvasTextShape'

class NonpersistentCanvasUrlShape(_CanvasUrlShape):
	__external_can_create__ = True
	mime_type = CanvasUrlShape.mime_type
	__external_class_name__ = 'CanvasUrlShape'

class NonpersistentCanvasPathShape(_CanvasPathShape):
	__external_can_create__ = True
	mime_type = CanvasPathShape.mime_type
	__external_class_name__ = 'CanvasPathShape'
