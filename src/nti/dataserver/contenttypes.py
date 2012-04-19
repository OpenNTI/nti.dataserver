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

from nti.dataserver import datastructures
from nti.dataserver.datastructures import StandardExternalFields, StandardInternalFields
from nti.dataserver import mimetype
from nti.dataserver import sharing
from nti.dataserver import interfaces as nti_interfaces

from zope import interface

def _get_entity( username, dataserver=None ):
	# importing globally is easily circular
	from nti.dataserver import users
	return users.Entity.get_entity( username, dataserver=dataserver )

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
			extDict['inReplyTo'] = datastructures.to_external_ntiid_oid( inReplyTo )

		extRefs = [] # Order matters
		for ref in self.references:
			extRefs.append( datastructures.to_external_ntiid_oid( ref ) )
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

# TODO: These objects should probably implement IZContained (__name__,__parent__). Otherwise they
# often wind up wrapped in container proxy objects, which is confusing. There may be
# traversal implications to that though, that need to be considered. See also classes.py
class _UserContentRoot(sharing.ShareableMixin, datastructures.ContainedMixin, datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	""" By default, if an update comes in with only new sharing information,
	and we have been previously saved, then we do not clear our
	other contents. Subclasses can override this by setting canUpdateSharingOnly
	to false.

	Subclasses must arrange for there to be an implementation of toExternalDictionary.

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
			warnings.warn( "Assuming datastructure layout" )
			if _get_entity( s, dataserver=dataserver ):
				target = _get_entity( s, dataserver=dataserver )
			elif hasattr( self.creator, 'getFriendsList' ):
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
		# The first time in, we need to allow container id (otherwise it may never get set)
		if not self.containerId:
			self.containerId = parsed.get( StandardExternalFields.CONTAINER_ID ) or parsed.get( StandardInternalFields.CONTAINER_ID )
		parsed = datastructures.stripSyntheticKeysFromExternalDictionary( dict( parsed ) )
		if self._is_update_sharing_only( parsed ):
			return

		self.clear()
		self.update( parsed )

	def __setitem__(self, key, value):
		if key in self.__dict__:
			return
		super( _UserArbitraryDataContentRoot, self ).__setitem__( key, value )

class Highlight(_UserContentRoot,datastructures.ExternalizableInstanceDict):
	# See comments above about being IZContained. We add it here to minimize the impact
	interface.implements( nti_interfaces.IZContained, nti_interfaces.IHighlight )
	_excluded_in_ivars_ = { 'AutoTags' } | datastructures.ExternalizableInstanceDict._excluded_in_ivars_

	__parent__ = None

	def __init__( self ):
		super(Highlight,self).__init__()
		self.top = 0
		self.left = 0
		# TODO: Determine the meaning of all these fields.
		self.startHighlightedFullText = ''
		self.startHighlightedText = ''
		self.startXpath = ''
		self.startAnchor = ''
		self.startOffset = 0
		self.endOffset = 0
		self.endAnchor = ''
		self.endXpath = ''

		self.endHighlightedText = ''
		self.endHighlightedFullText = ''

		self.anchorPoint = ''
		self.anchorType = ''

		# Tags. It may be better to use objects to represent
		# the tags and have a single list. The two-field approach
		# most directly matches what the externalization is.
		self.tags = ()
		self.AutoTags = ()

	def _get_name(self):
		return self.id
	def _set_name(self,name):
		self.id = name
	__name__ = property(_get_name,_set_name)


	def updateFromExternalObject( self, parsed, dataserver=None ):
		super(Highlight,self).updateFromExternalObject( parsed, dataserver=dataserver )
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



import html5lib
from html5lib import treewalkers, serializer, treebuilders
#from html5lib import filters
#from html5lib.filters import sanitizer
import lxml.etree



class _SliceDict(dict):
	"""
	There is a bug in html5lib 0.95: The _base.TreeWalker now returns
	a dictionary from normalizeAttrs. Some parts of the code, notably sanitizer.py 171
	haven't been updated from 0.90 and expect a list. They try to reverse it using a
	slice, and the result is a type error. We can fix this.
	"""

	def __getitem__( self, key ):
		# recognize the reversing slice, [::-1]
		if isinstance(key,slice) and key.start is None and key.stop is None and key.step == -1:
			return self.items()[::-1]
		return super(_SliceDict,self).__getitem__( key )

from html5lib.sanitizer import HTMLSanitizerMixin
# There is a bug in 0.95: the sanitizer converts attribute dicts
# to lists when they should stay dicts
_orig_sanitize = HTMLSanitizerMixin.sanitize_token
def _sanitize_token(self, token ):
	to_dict = False

	if token.get('name') in self.allowed_elements and isinstance( token.get( 'data' ), dict ):
		if not isinstance( token.get('data') , _SliceDict ):
			token['data'] = _SliceDict( {k[1]:v for k, v in token['data'].items()} )
		to_dict = True
	result = _orig_sanitize( self, token )
	if to_dict:
		# TODO: We're losing namespaces for attributes in this process
		result['data'] = {(None,k):v for k,v in result['data']}
	return result

HTMLSanitizerMixin.sanitize_token = _sanitize_token

# In order to be able to serialize a complete document, we
# must whitelist the root tags as of 0.95
# TODO: Maybe this means now we can parse and serialize in one step?
HTMLSanitizerMixin.allowed_elements.extend( ['html', 'head', 'body'] )

def _html5lib_tostring(doc,sanitize=True):
	walker = treewalkers.getTreeWalker("lxml")
	stream = walker(doc)
	# We can easily subclass filters.HTMLSanitizer to add more
	# forbidden tags, and some CSS things to filter. Then
	# we pass a treewalker over it to the XHTMLSerializer instead
	# of using the keyword arg.
	s = serializer.xhtmlserializer.XHTMLSerializer(inject_meta_charset=False,omit_optional_tags=False,sanitize=sanitize,quote_attr_values=True)
	output_generator = s.serialize(stream)
	string = ''.join(list(output_generator))
	return string

def sanitize_user_html( user_input, method='html' ):
	"""
	Given a user input string of plain text, HTML or HTML fragment, sanitize
	by removing unsupported/dangerous elements and doing some normalization.
	If it can be represented in plain text, do so.
	"""
	# We cannot sanitize and parse in one step; if there is already
	# HTML around it, then we wind up with escaped HTML as text:
	# <html>...</html> => <html><body>&lthtml&gt...&lt/html&gt</html>
	p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
	doc = p.parse( user_input )
	string = _html5lib_tostring( doc, sanitize=True )

	# Our normalization is pathetic.
	# replace unicode nbsps
	string = string.replace(u'\u00A0', ' ' )

	# Back to lxml to do some dom manipulation
	p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
	doc = p.parse( string )

	for node in doc.iter():
		# Turn top-level text nodes into paragraphs.
		if node.tag == 'p' and node.tail:
			tail = node.tail
			node.tail = None
			p = lxml.etree.Element( node.tag, node.attrib )
			p.text = tail
			node.addnext( p )

		# Strip spans that are the empty (they used to contain style but no longer)
		elif node.tag == 'span' and len(node) == 0 and not node.text:
			node.getparent().remove( node )

		# Spans that are directly children of a paragraph (and so could not contain
		# other styling through inheritance) that have the pad's default style get that removed
		# so they render as default on the browser as well
		elif node.tag == 'span' and node.getparent().tag == 'p' and node.get( 'style' ) == 'font-family: \'Helvetica\'; font-size: 12pt; color: black;':
			del node.attrib['style']

	if method == 'text':
		return lxml.etree.tostring( doc, method='text' )

	string = _html5lib_tostring( doc, sanitize=False )
	# If we can go back to plain text, do so.
	normalized = string[len('<html><head></head><body>'): 0 - len('</body></html>')]
	while normalized.endswith( '<br />' ):
		# remove trailing breaks
		normalized = normalized[0:-6]
	# If it has no more tags, we can be plain text.
	if '<' not in normalized:
		string = normalized.strip()
	else:
		string = "<html><body>" + normalized + "</body></html>"
	return string


class Note(ThreadableExternalizableMixin, Highlight):
	interface.implements(nti_interfaces.INote)

	def __init__(self):
		super(Note,self).__init__()
		self.body = ("",)

	def toExternalDictionary( self ):
		result = super(Note,self).toExternalDictionary()
		# In our initial state, don't try to send empty body/text
		if self.body == ('',):
			result.pop( 'body' )

		return result

	def updateFromExternalObject( self, parsed, dataserver=None ):
		# Only updates to the body are accepted
		parsed.pop( 'text', None )

		super(Note, self).updateFromExternalObject( parsed, dataserver=dataserver )
		if self._is_update_sharing_only( parsed ):
			return

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

			# Sanitize the body
			self.body = [sanitize_user_html(x) if isinstance(x,six.string_types) else x
							for x
							in self.body]

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
			# (Be a bit defensive about bad inReplyTo)
			if not hasattr( self.inReplyTo, 'getFlattenedSharingTargetNames' ):
				raise AttributeError( 'Illegal value for inReplyTo: %s (%s)' % datastructures.toExternalOID(self.inReplyTo), self.inReplyTo )
			sharingTargetNames = set( self.inReplyTo.getFlattenedSharingTargetNames() )
			sharingTargetNames.add( getattr( self.inReplyTo.creator, 'username', None ) )
			sharingTargetNames.discard( creatorName )
			sharingTargetNames.discard( None )

			for name in sharingTargetNames:
				ent = _get_entity( name, dataserver=dataserver )
				target = ent or name
				self.addSharingTarget( target, self.creator )

			# Now some other things we want to inherit if possible
			for copy in ('anchorPoint','anchorType','left','top'):
				val = getattr( self.inReplyTo, copy, getattr( self, copy, None ) )
				if val is not None:
					setattr( self, copy, val )

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
		# TODO: Need a mimetype for these guys.
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
			self.text = sanitize_user_html( self.text, method='text' )


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
