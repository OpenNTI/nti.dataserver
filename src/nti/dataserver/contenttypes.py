#!/usr/bin/env python
""" This module defines the content types that users can create within the system. """
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )

import persistent
import warnings
import collections
import numbers

from persistent.list import PersistentList
import six
import urlparse
import base64

from nti.externalization.interfaces import IExternalObject
from nti.externalization.externalization import stripSyntheticKeysFromExternalDictionary, toExternalObject
from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.externalization import internalization

from nti.dataserver import datastructures
from nti.dataserver import mimetype
from nti.dataserver import sharing
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.ntiids import ntiids

from nti.contentfragments import interfaces as frg_interfaces
from nti.contentfragments import censor

from zope import interface
from zope.deprecation import deprecate
from zope import component
from zope.annotation import interfaces as an_interfaces

def _get_entity( username, dataserver=None ):
	return users.Entity.get_entity( username, dataserver=dataserver, _namespace=users.User._ds_namespace )

class ThreadableMixin(object):
	""" Defines an object that is client-side threadable. These objects are
	threaded like email (RFC822?). We assume a single parent and
	maintain a list of parents in order up to the root (or the last
	thing that was threadable. """

	__external_oids__ = ['inReplyTo', 'references']

	# Our one single parent
	_inReplyTo = None
	# Our chain of references back to the root
	_references = ()

	def __init__(self):
		super(ThreadableMixin,self).__init__()

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
			if not self._references:
				self._references = PersistentList()
			self._references.append( persistent.wref.WeakRef( value ) )

	def clearReferences( self ):
		if self._references:
			del self._references

class ThreadableExternalizableMixin(ThreadableMixin):
	"""
	Extends :class:`ThreadableMixin` with support for externalizing to and from a dictionary.
	"""
	def toExternalObject(self):
		extDict = super(ThreadableExternalizableMixin,self).toExternalObject()
		assert isinstance( extDict, collections.Mapping )
		inReplyTo = self.inReplyTo
		if inReplyTo is not None:
			extDict['inReplyTo'] = to_external_ntiid_oid( inReplyTo )

		extRefs = [] # Order matters
		for ref in self.references:
			extRefs.append( to_external_ntiid_oid( ref ) )
		if extRefs:
			extDict['references'] = extRefs
		return extDict

	def updateFromExternalObject( self, parsed, **kwargs ):
		assert isinstance( parsed, collections.Mapping )
		inReplyTo = parsed.pop( 'inReplyTo', None )
		references = parsed.pop( 'references', [] )
		super(ThreadableExternalizableMixin, self).updateFromExternalObject( parsed, **kwargs )

		self.inReplyTo = inReplyTo
		self.clearReferences()
		for ref in references:
			self.addReference( ref )

# TODO: These objects should probably implement IZContained (__name__,__parent__). Otherwise they
# often wind up wrapped in container proxy objects, which is confusing. There may be
# traversal implications to that though, that need to be considered. See also classes.py
@interface.implementer(nti_interfaces.IModeledContent,IExternalObject)
class _UserContentRoot(sharing.ShareableMixin, datastructures.ContainedMixin, datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	""" By default, if an update comes in with only new sharing information,
	and we have been previously saved, then we do not clear our
	other contents. Subclasses can override this by setting canUpdateSharingOnly
	to false.

	Subclasses must arrange for there to be an implementation of toExternalDictionary.

	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass


	canUpdateSharingOnly = True
	__external_can_create__ = True

	def __init__(self):
		super(_UserContentRoot,self).__init__()

	def toExternalObject( self ):
		extDict = getattr( self, 'toExternalDictionary' )()

		sharedWith = toExternalObject( self.flattenedSharingTargetNames )
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
		parsed = stripSyntheticKeysFromExternalDictionary( dict( parsed ) )
		return len(parsed) == 0 and self.canUpdateSharingOnly and self._p_jar

	def updateFromExternalObject( self, ext_parsed, *args, **kwargs ):
		assert isinstance( ext_parsed, collections.Mapping )
		# Remove some things that may come in (in a copy!)
		parsed = ext_parsed

		# It's important that they stay stripped so that our
		# canUpdateSharingOnly check works (len = 0)

		# Replace sharing with the incoming data.
		sharedWith = parsed.pop( 'sharedWith', () )
		targets = set()
		for s in sharedWith or ():
			target = s
			if _get_entity( s ):
				target = _get_entity( s )
			elif hasattr( self.creator, 'getFriendsList' ):
				# This branch is semi-deprecated. They should send in
				# the NTIID of the list...once we apply security here
				target = self.creator.getFriendsList( s )

			if (target is s or target is None) and ntiids.is_valid_ntiid_string( s ):
				# Any thing else that is a username iterable,
				# in which we are contained (e.g., a class section we are enrolled in)
				# This last clause is our nod to security; need to be firmer

				obj = ntiids.find_object_with_ntiid( s )
				obj = nti_interfaces.IUsernameIterable( obj, None )
				if obj:
					obj = tuple(obj) # expand the iterable to something hashable
					if getattr( self.creator, 'username', self.creator) in obj and self.creator is not None:
						target = obj
					else:
						target = s = None

			# TODO: We should really only add target, and only if it
			# is non-none, right? Otherwise we are falsely implying sharing
			# happened when it really didn't
			targets.add( target or s )
		self.updateSharingTargets( targets )

		if self._is_update_sharing_only( parsed ):
			# In this state, we have received an update only for sharing.
			# and so do not need to do anything else. We're a saved
			# object already. If we're not saved already, we cannot
			# be created with just this
			pass
		elif len(stripSyntheticKeysFromExternalDictionary( dict( parsed ) )) == 0:
			raise ValueError( "Updating non-saved object: The body must have some data, cannot be empty" )

		s = super(_UserContentRoot,self)
		if hasattr( s, 'updateFromExternalObject' ):
			# Notice we pass on the original dictionary
			getattr( s, 'updateFromExternalObject' )(ext_parsed, *args, **kwargs )

class _HighlightBWC(object):
	"""
	Defines read-only properties that are included in a highlight
	to help backwards compatibility.
	"""

	top = left = startOffset = endOffset = property( deprecate( "Use the applicableRange" )( lambda self: 0 ) )

	highlightedText = startHighlightedFullText = startHighlightedText = endHighlightedText = endHighlightedFullText = property( deprecate( "Use the selectedText" )( lambda self: getattr( self, 'selectedText' ) ) )

	startXpath = startAnchor = endAnchor = endXpath = anchorPoint = anchorType = property( deprecate( "Use the applicableRange" )( lambda self: '' ) )

@interface.implementer(nti_interfaces.IZContained, nti_interfaces.ISelectedRange)
class SelectedRange(_UserContentRoot,ExternalizableInstanceDict):
	# See comments above about being IZContained. We add it here to minimize the impact

	_excluded_in_ivars_ = { 'AutoTags' } | ExternalizableInstanceDict._excluded_in_ivars_

	selectedText = ''
	applicableRange = None
	tags = ()
	AutoTags = ()
	_update_accepts_type_attrs = True
	__parent__ = None

	def __init__( self ):
		super(SelectedRange,self).__init__()
		# To get in the dict for externalization
		self.selectedText = ''
		self.applicableRange = None

		# Tags. It may be better to use objects to represent
		# the tags and have a single list. The two-field approach
		# most directly matches what the externalization is.
		self.tags = ()
		self.AutoTags = ()

	__name__ = property(lambda self: getattr( self, 'id'), lambda self, name: setattr( self, 'id', name ))

	# While we are transitioning over from instance-dict-based serialization
	# to schema based serialization and validation, we handle update validation
	# ourself through these two class attributes. You may extend the list of fields
	# to validate in your subclass if you also set the schema to the schema that defines
	# those fields (and inherits from ISelectedRange).
	# This validation provides an opportunity for adaptation to come into play as well,
	# automatically taking care of things like sanitizing user input
	_schema_fields_to_validate_ = ('applicableRange', 'selectedText')
	_schema_to_validate_ = nti_interfaces.ISelectedRange

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		parsed.pop( 'AutoTags', None )
		super(SelectedRange,self).updateFromExternalObject( parsed, *args, **kwargs )
		__traceback_info__ = parsed
		for k in self._schema_fields_to_validate_:
			value = getattr( self, k )
			# pass the current value, and call the return value (if there's no exception)
			# in case adaptation took place
			internalization.validate_named_field_value( self, self._schema_to_validate_, k, value )()


		if 'tags' in parsed:
			# we lowercase and sanitize tags. Our sanitization here is really
			# cheap and discards html symbols
			temp_tags = { t.lower() for t in parsed['tags'] if '>' not in t and '<' not in t and '&' not in t }
			if not temp_tags:
				self.tags = ()
			else:
				# Preserve an existing mutable object if we have one
				if not self.tags:
					self.tags = []
				del self.tags[:]
				self.tags.extend( temp_tags )

@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange, _HighlightBWC):

	style = 'plain'

	def __init__( self ):
		super(Highlight,self).__init__()
		# To get in the dict for externalization
		self.style = self.style

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(Highlight,self).updateFromExternalObject( parsed, *args, **kwargs )
		if 'style' in parsed:
			nti_interfaces.IHighlight['style'].validate( parsed['style'] )

@interface.implementer(nti_interfaces.IRedaction)
class Redaction(SelectedRange):

	replacementContent = None
	redactionExplanation = None
	_schema_fields_to_validate_ = SelectedRange._schema_fields_to_validate_ + ('replacementContent','redactionExplanation')
	_schema_to_validate_ = nti_interfaces.IRedaction

@interface.implementer(nti_interfaces.INote,
					    # requires annotations
					   nti_interfaces.ILikeable,
					   nti_interfaces.IFavoritable,
					   nti_interfaces.IFlaggable,
					   # provides annotations
					   an_interfaces.IAttributeAnnotatable )
class Note(ThreadableExternalizableMixin, Highlight):


	# A sequence of properties we would like to copy from the parent
	# when a child reply is created. If the child already has them, they
	# are left alone.
	# This consists of the anchoring properties
	_inheritable_properties_ = ( 'applicableRange', )
	style = 'suppressed'

	def __init__(self):
		super(Note,self).__init__()
		self.body = ("",)

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(Note,self).toExternalDictionary(mergeFrom=mergeFrom)
		# In our initial state, don't try to send empty body/text
		if self.body == ('',):
			result.pop( 'body' )

		return result

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		# Only updates to the body are accepted
		parsed.pop( 'text', None )

		super(Note, self).updateFromExternalObject( parsed, *args, **kwargs )
		if self._is_update_sharing_only( parsed ):
			return

		self.updateLastMod()
		# Support text and body as input
		if 'body' in parsed:
			# Support raw body, not wrapped
			if isinstance( parsed['body'], six.string_types ):
				self.body = ( parsed['body'], )
			assert len(self.body) > 0
			# convert mutable lists to immutable tuples
			self.body = tuple( self.body )

			# Verify that the body contains supported types, if
			# sent from the client.
			for x in self.body:
				assert (isinstance(x, six.string_types) and len(x) > 0) or isinstance(x,Canvas)

			# Sanitize the body. Anything that can become a fragment, do so, incidentally
			# sanitizing and censoring it along the way.
			self.body = [censor.censor_assign( frg_interfaces.IUnicodeContentFragment( x, x ), self, 'body' )
							for x
							in self.body]

		# If we are newly created, and a reply, then
		# we want to use our policy settings to determine the sharing
		# of the new note. This is because our policy settings
		# may be user/community/context specific.
		if not self._p_mtime and self.inReplyTo:
			self.clearSharingTargets() # ignore anything incoming
			creatorName = getattr( self.creator, 'username', None )
			# Current policy is to copy the sharing settings
			# of the parent, and share back to the parent's creator,
			# only making sure not to share with ourself since that's weird
			# (Be a bit defensive about bad inReplyTo)
			if not hasattr( self.inReplyTo, 'flattenedSharingTargetNames' ):
				raise AttributeError( 'Illegal value for inReplyTo: %s (%s)' % datastructures.toExternalOID(self.inReplyTo), self.inReplyTo )
			sharingTargetNames = set( self.inReplyTo.flattenedSharingTargetNames )
			sharingTargetNames.add( getattr( self.inReplyTo.creator, 'username', None ) )
			sharingTargetNames.discard( creatorName )
			sharingTargetNames.discard( None )

			for name in sharingTargetNames:
				ent = _get_entity( name )
				target = ent or name
				self.addSharingTarget( target, self.creator )

			# Now some other things we want to inherit if possible
			for copy in self._inheritable_properties_:
				val = getattr( self.inReplyTo, copy, getattr( self, copy, None ) )
				if val is not None:
					setattr( self, copy, val )

#####
# Whiteboard shapes
#####
@interface.implementer(nti_interfaces.ICanvas,nti_interfaces.IZContained)
class Canvas(ThreadableExternalizableMixin, _UserContentRoot, ExternalizableInstanceDict):

	# TODO: We're not trying to resolve any incoming external
	# things. Figure out how we want to do incremental changes
	# (pushing new shapes while drawing). Should we take the whole thing every
	# time (and then look for equal object that we already have)? Accept POSTS
	# of shapes into this object as a "container"?
	__parent__ = None
	__name__ = None

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
		try:
			return self.shapeList == other.shapeList
		except AttributeError:
			return NotImplemented


def _make_external_value_object( external ):
	external.pop( 'Last Modified', None )
	external.pop( 'OID', None )
	external.pop( 'ID', None )
	external.pop( 'CreatedTime', None )
	external.pop( 'Creator', None )
	return external

class CanvasAffineTransform(ExternalizableInstanceDict):
	"""
	Represents the 6 values required in an 2-D affine transform:
	\|a  b  0|
	\|c  d  0|
	\|tx ty 1|

	Treated are like structs, compared by value, not identity. They are
	never standalone, so many of their external fields are lacking.
	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

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
		# TODO: Need a mimetype for these guys.
		return _make_external_value_object( super(CanvasAffineTransform,self).toExternalDictionary( mergeFrom=mergeFrom ) )

	def __eq__( self, other ):
		try:
			return all( [getattr(self, x) == getattr(other,x) for x in self.__dict__] )
		except AttributeError:
			return NotImplemented


class CanvasShape(_UserContentRoot,ExternalizableInstanceDict):
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
		self._stroke_rgba = [1.0, 1.0, 1.0, 1.0]
		self._fill_rgba = [1.0, 1.0, 1.0, 0.0]
		# stroke width is the same both places, and stored in pts.
		self._stroke_width = 1.0

	def __setstate__( self, state ):
		super(CanvasShape,self).__setstate__( state )
		if not hasattr( self, '_stroke_rgba' ):
			self._stroke_rgba = [1.0, 1.0, 1.0, 1.0]
		if not hasattr( self, '_fill_rgba' ):
			self._fill_rgba = [1.0, 1.0, 1.0, 0.0]
		if not hasattr( self, '_stroke_width' ):
			self._stroke_width = 1.0

	def get_transform( self ):
		result = CanvasAffineTransform( )
		for x in result.__dict__:
			setattr( result, x, getattr( self, '_' + x ) )
		return result
	def set_transform( self, matrix ):
		__traceback_info__ = matrix
		assert isinstance( matrix, CanvasAffineTransform )
		for x in matrix.__dict__:
			setattr( self, '_' + x, matrix.__dict__[x] )
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
				self._p_changed = True

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
		# TODO: This is a lousy comparison
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
		tbf = self.text
		super(CanvasTextShape,self).updateFromExternalObject( *args, **kwargs )
		assert isinstance( self.text, six.string_types )
		if self.text != tbf:
			self.text = component.getAdapter( self.text, frg_interfaces.IUnicodeContentFragment, name='text' )


class CanvasUrlShape(CanvasShape):

	def __init__( self, url='' ):
		super(CanvasUrlShape, self).__init__( )
		self.url = url

	def updateFromExternalObject( self, *args, **kwargs ):
		super(CanvasUrlShape,self).updateFromExternalObject( *args, **kwargs )

	def _get_url(self):
		if '_head' in self.__dict__:
			return self._head + ',' + base64.b64encode( self._raw_tail )
		return self.__dict__[ 'url' ]
	def _set_url(self,nurl):
		if not nurl:
			self.__dict__.pop( '_head', None )
			self.__dict__.pop( '_raw_tail', None )
			self.__dict__['url'] = nurl
			return

		parsed = urlparse.urlparse( nurl )
		assert parsed.scheme == 'data'
		if parsed.path.split( ';' )[-1].startswith( 'base64' ):
			# Un-base 64 things for more compact storage
			head = nurl[0:nurl.index(',')]
			tail = nurl[nurl.index(',')+1:]
			bts = base64.b64decode( tail )
			self._head = head
			self._raw_tail = bts
			# By keeping url in __dict__, toExternalDictionary
			# still does the right thing
			self.__dict__['url'] = None
		else:
			self.__dict__['url'] = nurl
	url = property(_get_url,_set_url)

	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, len(self.url))

class CanvasPathShape(CanvasShape):

	def __init__( self, closed=True, points=() ):
		super(CanvasPathShape,self).__init__()
		self.closed = closed
		self.points = points

	def updateFromExternalObject(self, *args, **kwargs ):
		super(CanvasPathShape,self).updateFromExternalObject( *args, **kwargs )
		assert (isinstance( self.closed, bool ) or self.closed == 0 or self.closed == 1)
		if self.closed == 0 or self.closed == 1:
			self.closed = bool(self.closed)
		for i in self.points:
			assert isinstance( i, numbers.Real )
		assert (len(self.points) % 2) == 0 # Must be even number of pairs

	def __eq__( self, other ):
		return super(CanvasPathShape,self).__eq__( other ) \
			and self.closed == getattr(other,'closed',None) \
			and self.points == getattr(other,'points',None)


# Support for legacy quiz posting
from quizzes import QuizResult
quizresult = QuizResult
