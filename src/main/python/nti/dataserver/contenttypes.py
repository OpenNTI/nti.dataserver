""" This module defines the content types that users can create within the system. """

import persistent
import collections
import numbers
from persistent.list import PersistentList

import users
import datastructures
from . import mimetype

from . import interfaces as nti_interfaces
from zope import interface

class ThreadableMixin(object):
	""" Defines an object that is client-side threadable. These objects are
	threaded like email (RFC822?). We assume a single parent and
	maintain a list of parents in order up to the root (or the last
	thing that was threadable. """

	__external_oids__ = ['inReplyTo', 'references']

	def __init__(self):
		super(ThreadableMixin,self).__init__()
		# Our one single parent
		self._inReplyTo = None
		# Our chain of references back to the root
		self._references = []

	def getInReplyTo(self):
		return self._inReplyTo() if self._inReplyTo else None

	def setInReplyTo( self, value ):
		self._inReplyTo = persistent.wref.WeakRef( value ) if value is not None else None

	inReplyTo = property( getInReplyTo, setInReplyTo )

	@property
	def references(self):
		return [x() for x in self._references if x() is not None]

	def addReference( self, value ):
		if value is not None:
			self._references.append( persistent.wref.WeakRef( value ) )

	def clearReferences( self ):
		del self._references[0:]

class ThreadableExternalizableMixin(ThreadableMixin):
	"""
	Extends :class:`ThreadableMixin` with support for externalizing to and from a dictionary.
	"""
	def toExternalObject(self):
		extDict = super(ThreadableExternalizableMixin,self).toExternalObject()
		assert isinstance( extDict, collections.Mapping )
		inReplyTo = self.inReplyTo
		if inReplyTo is not None:
			extDict['inReplyTo'] = datastructures.toExternalOID( inReplyTo )

		extRefs = [] # Order matters
		for ref in self.references:
			extRefs.append( datastructures.toExternalOID( ref ) )
		if extRefs:
			extDict['references'] = extRefs
		return extDict

	def updateFromExternalObject( self, parsed, dataserver=None ):
		assert isinstance( parsed, collections.Mapping )
		inReplyTo = parsed.pop( 'inReplyTo', None )
		references = parsed.pop( 'references', [] )
		super(ThreadableExternalizableMixin, self).updateFromExternalObject( parsed, dataserver=dataserver )

		self.inReplyTo = inReplyTo
		self.clearReferences()
		for ref in references:
			self.addReference( ref )

class _UserContentRoot(users.ShareableMixin, datastructures.ContainedMixin, datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	""" By default, if an update comes in with only new sharing information,
	and we have been previously saved, then we do not clear our
	other contents. Subclasses can override this by setting canUpdateSharingOnly
	to false.

	Subclasses must arrange for their to be an implementation of toExternalDictionary.

	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.IModeledContent,nti_interfaces.IExternalObject)

	canUpdateSharingOnly = True
	__external_can_create__ = True

	def __init__(self):
		super(_UserContentRoot,self).__init__()

	def toExternalObject( self ):
		extDict = getattr( self, 'toExternalDictionary' )()
		# TODO: Should we do the same resolution and wrapping that
		# friends lists do? That would be difficult here
		# Be triply sure this is a unique set.
		sharedWith = list( set( datastructures.toExternalObject( self.getFlattenedSharingTargetNames() ) ) )
		if sharedWith:
			extDict['sharedWith'] = sharedWith
		return extDict

	def _is_update_sharing_only( self, parsed ):
		"""
		Call this after invoking this objects (super's) implementation of
		updateFromExternalObject. If it returns a true value,
		you should take no action.
		"""
		# TODO: I don't like this. It requires all subclasses
		# to be complicit
		parsed = datastructures.stripSyntheticKeysFromExternalDictionary( dict( parsed ) )
		return len(parsed) == 0 and self.canUpdateSharingOnly and self._p_jar

	def updateFromExternalObject( self, ext_parsed, dataserver=None ):
		assert isinstance( ext_parsed, collections.Mapping )
		# Remove some things that may come in (in a copy!)
		parsed = ext_parsed

		# It's important that they stay stripped so that our
		# canUpdateSharingOnly check works (len = 0)

		# Replace sharing with the incoming data.
		sharedWith = parsed.pop( 'sharedWith', () )
		self.clearSharingTargets()
		for s in sharedWith or ():
			target = s
			if dataserver and s in dataserver.root['users']:
				target = dataserver.root['users'][s]
			elif isinstance( self.creator, users.User ):
				target = self.creator.getFriendsList( s )
			self.addSharingTarget( target or s, self.creator )

		if self._is_update_sharing_only( parsed ):
			# In this state, we have received an update only for sharing.
			# and so do not need to do anything else. We're a saved
			# object already. If we're not saved already, we cannot
			# be created with just this
			pass
		elif len(datastructures.stripSyntheticKeysFromExternalDictionary( dict( parsed ) )) == 0:
			raise ValueError( "Updating non-saved object: The body must have some data, cannot be empty" )

		s = super(_UserContentRoot,self)
		if hasattr( s, 'updateFromExternalObject' ):
			# Notice we pass on the original dictionary
			getattr( s, 'updateFromExternalObject' )(ext_parsed, dataserver=dataserver )

class _UserArbitraryDataContentRoot(_UserContentRoot, datastructures.IDItemMixin, datastructures.ModDateTrackingPersistentMapping):
	""" This class is for legacy support. It allows
	storing any data in this object, using it as a map."""

	def __init__(self):
		super(_UserArbitraryDataContentRoot,self).__init__()

	def updateFromExternalObject( self, parsed, dataserver=None ):
		super( _UserArbitraryDataContentRoot, self ).updateFromExternalObject( parsed, dataserver=dataserver )
		parsed = datastructures.stripSyntheticKeysFromExternalDictionary( dict( parsed ) )
		if self._is_update_sharing_only( parsed ):
			return

		self.clear()
		self.update( parsed )

	def __setitem__(self, key, value):
		if key in self.__dict__:
			return
		super( _UserArbitraryDataContentRoot, self ).__setitem__( key, value )

class Highlight(_UserArbitraryDataContentRoot):
	pass


class Note(ThreadableExternalizableMixin, Highlight):
	interface.implements(nti_interfaces.INote)

	# TODO: Migrate this off arbitrary data and onto something stable.
	def __init__(self):
		super(Note,self).__init__()
		self['body'] = ('')

	def __setstate__( self, state ):
		super(Note,self).__setstate__( state )
		# Migration from old text to new body
		if 'text' in self and 'body' not in self:
			self['body'] = [ self['text'] ]


	def updateFromExternalObject( self, parsed, dataserver=None ):
		super(Note, self).updateFromExternalObject( parsed, dataserver=dataserver )
		if self._is_update_sharing_only( parsed ):
			return

		# Support text and body as input
		if 'body' in parsed:
			# Support raw body, not wrapped
			if isinstance( parsed['body'], basestring ):
				self['body'] = [ parsed['body'] ]
			self['text'] = self['body'][0]
		elif 'text' in parsed:
			# Body always trumps. But if not present,
			# text must be there.
			self['body'] = [ self['text'] ]

		# Verify that the body contains supported types
		assert all( [isinstance(x, (basestring,Canvas)) for x in self['body']] )

		# If we are newly created, and a reply, then
		# we want to use our policy settings to determine the sharing
		# of the new note. This is because our policy settings
		# may be user/community/context specific.
		if not self._p_jar and self.inReplyTo:
			self.clearSharingTargets() # ignore anything incoming
			creatorName = getattr( self.creator, 'username', None )
			# Current policy is to copy the sharing settings
			# of the parent, and share back to the parent's creator,
			# only making sure not to share with ourself since that's weird
			sharingTargetNames = set( self.inReplyTo.getFlattenedSharingTargetNames() )
			sharingTargetNames.add( getattr( self.inReplyTo.creator, 'username', None ) )
			sharingTargetNames.discard( creatorName )
			sharingTargetNames.discard( None )

			for name in sharingTargetNames:
				ent = users.Entity.get_entity( name, dataserver=dataserver )
				target = ent or name
				self.addSharingTarget( target, self.creator )

			# Now some other things we want to inherit if possible
			for copy in ('anchorPoint','anchorType','left','top'):
				val = self.inReplyTo.get( copy, self.get( copy ) )
				if val is not None:
					self[copy] = val

#####
# Whiteboard shapes
#####

class Canvas(ThreadableExternalizableMixin, _UserContentRoot, datastructures.ExternalizableInstanceDict):

	interface.implements( nti_interfaces.ICanvas )
	# TODO: We're not trying to resolve any incoming external
	# things. Figure out how we want to do incremental changes
	# (pushing new shapes while drawing). Should we take the whole thing every
	# time (and then look for equal object that we already have)? Accept POSTS
	# of shapes into this object as a "container"?

	def __init__(self):
		super(Canvas,self).__init__()
		self.shapeList = PersistentList()

	def append( self, shape ):
		self.shapeList.append( shape )

	def __getitem__( self, i ):
		return self.shapeList[i]

	def updateFromExternalObject( self, *args, **kwargs ):
		super(Canvas,self).updateFromExternalObject( *args, **kwargs )
		assert all( (isinstance( x, CanvasShape ) for x in self.shapeList) )

	def __eq__( self, other ):
		# TODO: Super properties?
		return isinstance( other, Canvas ) and self.shapeList == other.shapeList


def _make_external_value_object( external ):
	external.pop( 'Last Modified', None )
	external.pop( 'OID', None )
	external.pop( 'ID', None )
	external.pop( 'CreatedTime', None )
	external.pop( 'Creator', None )
	return external

class CanvasAffineTransform(datastructures.ExternalizableInstanceDict):
	"""
	Represents the 6 values required in an 2-D affine transform:
	\|a  b  0|
	\|c  d  0|
	\|tx ty 1|

	Treated are like structs, compared by value, not identity. They are
	never standalone, so many of their external fields are lacking.
	"""
	__external_can_create__ = True
	def __init__( self ):
		"""
		Initializes to the identity transform.
		"""
		super(CanvasAffineTransform,self).__init__()
		self.a = 1
		self.b = 0
		self.c = 0
		self.d = 1
		self.tx = 0
		self.ty = 0

	def updateFromExternalObject( self, *args, **kwargs ):
		super(CanvasAffineTransform,self).updateFromExternalObject( *args, **kwargs )
		for x in self.__dict__:
			assert isinstance( getattr( self, x ), numbers.Number )

	def toExternalDictionary( self, mergeFrom=None ):
		return _make_external_value_object( super(CanvasAffineTransform,self).toExternalDictionary( mergeFrom=mergeFrom ) )

	def __eq__( self, other ):
		if not isinstance( other, CanvasAffineTransform ): return False
		return all( [getattr(self, x) == getattr(other,x) for x in self.__dict__] )


class CanvasShape(_UserContentRoot,datastructures.ExternalizableInstanceDict):
	# We generate the affine transform on demand; we don't store it
	# to avoid object overhead.

	def __init__( self ):
		super(CanvasShape,self).__init__( )
		# Matrix fields. Initialize as identity.
		self._a = 1
		self._b = 0
		self._c = 0
		self._d = 1
		self._tx = 0
		self._ty = 0

		# We expose stroke and fill properties optimized
		# for both Web and iPad. The iPad format is a superset
		# of the other format and so that's what we store
		self._stroke_rgba = [255.0, 255.0, 255.0, 1.0]
		self._fill_rgba = [255.0, 255.0, 255.0, 0.0]
		# stroke width is the same both places, and stored in pts.
		self._stroke_width = 1.0

	def __setstate__( self, state ):
		super(CanvasShape,self).__setstate__( state )
		if not hasattr( self, '_stroke_rgba' ):
			self._stroke_rgba = [255.0, 255.0, 255.0, 1.0]
		if not hasattr( self, '_fill_rgba' ):
			self._fill_rgba = [255.0, 255.0, 255.0, 0.0]
		if not hasattr( self, '_stroke_width' ):
			self._stroke_width = 1.0

	def get_transform( self ):
		result = CanvasAffineTransform( )
		for x in result.__dict__:
			setattr( result, x, getattr( self, '_' + x ) )
		return result
	def set_transform( self, matrix ):
		assert isinstance( matrix, CanvasAffineTransform )
		for x in matrix.__dict__:
			setattr( self, '_' + x, matrix.__dict__[x] )
	transform = property( get_transform, set_transform )

	@property
	def strokeRGBAColor(self):
		return ' '.join( map( str, self._stroke_rgba ) )
	@property
	def fillRGBAColor(self):
		return ' '.join( map( str, self._fill_rgba ) )
	@property
	def strokeColor(self):
		return "rgb({:.1f},{:.1f},{:.1f})".format( *self._stroke_rgba[0:3] )
	@property
	def strokeOpacity(self):
		return self._stroke_rgba[3]
	@property
	def strokeWidth(self):
		return "%.1fpt" % self._stroke_width
	@property
	def fillColor(self):
		return "rgb({:.1f},{:.1f},{:.1f})".format( *self._fill_rgba[0:3] )
	@property
	def fillOpacity(self):
		return self._fill_rgba[3]

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(CanvasShape,self).updateFromExternalObject( parsed, *args, **kwargs )
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
				r, g, b = map( float, stroke_color.strip()[4:-1].split( ',' ) )
				assert( 0.0 <= r <= 255.0 )
				assert( 0.0 <= g <= 255.0 )
				assert( 0.0 <= b <= 255.0 )
				arr[0], arr[1], arr[2] = r, g, b
				self._p_changed = True
			if stroke_opacity is not None:
				assert( 0.0 <= stroke_opacity <= 1.0 )
				# opacity and alpha are exactly the same,
				# 0.0 fully transparent, 1.0 fully opaque
				arr[3] = stroke_opacity
				self._p_changed = True

		def update_from_rgba( arr, string ):
			r, g, b, a = map( float, string.split( ' ' ) )
			assert( 0.0 <= r <= 255.0 )
			assert( 0.0 <= g <= 255.0 )
			assert( 0.0 <= b <= 255.0 )
			arr[0], arr[1], arr[2] = r, g, b
			assert( 0.0 <= a <= 1.0 )
			arr[3] = a
			self._p_changed = True

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
			if isinstance( stroke_width, basestring ) and stroke_width.endswith( 'pt' ):
				stroke_width = stroke_width[0:-2]
			stroke_width = float(stroke_width)
			assert( stroke_width >= 0.0 )
			self._stroke_width = stroke_width

	def toExternalDictionary( self, mergeFrom=None ):
		# Implementation note: For now, because we are not
		# doing anything fancy with keeping track of identical objects
		# when we update a canvas, we are also eliding these same fields like Point.
		mergeFrom = mergeFrom or {}
		mergeFrom['transform'] = self.transform.toExternalDictionary()

		mergeFrom['strokeRGBAColor'] = self.strokeRGBAColor
		mergeFrom['fillRGBAColor'] = self.fillRGBAColor

		mergeFrom['strokeColor'] = self.strokeColor
		mergeFrom['strokeOpacity'] = self.strokeOpacity
		mergeFrom['strokeWidth'] = self.strokeWidth

		mergeFrom['fillColor'] = self.fillColor
		mergeFrom['fillOpacity'] = self.fillOpacity

		return _make_external_value_object( super(CanvasShape,self).toExternalDictionary( mergeFrom=mergeFrom ) )

	def __eq__( self, other ):
		# Implementation note: when toExternalDictionary changes,
		# this method should change too
		return self.__class__ == other.__class__ and self.transform == other.transform

class CanvasCircleShape(CanvasShape): pass
class CanvasPolygonShape(CanvasShape):

	def __init__(self, sides=4 ):
		super(CanvasPolygonShape,self).__init__()
		self.sides = sides

	def updateFromExternalObject( self, *args, **kwargs ):
		super(CanvasPolygonShape,self).updateFromExternalObject( *args, **kwargs )
		assert isinstance( self.sides, numbers.Integral )

	def __eq__( self, other ):
		return super(CanvasPolygonShape,self).__eq__( other ) and self.sides == other.sides

class CanvasTextShape(CanvasShape):

	def __init__( self, text='' ):
		super(CanvasTextShape, self).__init__( )
		self.text = text

	def updateFromExternalObject( self, *args, **kwargs ):
		super(CanvasTextShape,self).updateFromExternalObject( *args, **kwargs )
		assert isinstance( self.text, basestring )


# Support for legacy quiz posting
from quizzes import QuizResult
quizresult = QuizResult
