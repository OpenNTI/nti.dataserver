#!/usr/bin/env python
"""
Definition of the Note object.
"""
from __future__ import print_function, unicode_literals

import six

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.internalization import update_from_external_object

from nti.ntiids.ntiids import find_object_with_ntiid

from zope import component
from zope import interface


from zope.annotation import interfaces as an_interfaces

import zope.schema.interfaces
from zope.schema.fieldproperty import FieldProperty
from .highlight import Highlight
from .threadable import ThreadableMixin
from .base import _make_getitem

class BodyFieldProperty(FieldProperty):
	# This currently exists for legacy support (test cases)

	def __init__( self, field, name=None ):
		super(BodyFieldProperty,self).__init__( field, name=name )
		self._field = field

	def __set__( self, inst, value ):
		if value and isinstance( value, list ):
			value = tuple(value)
		try:
			super(BodyFieldProperty,self).__set__( inst, value )
		except zope.schema.interfaces.ValidationError:
			# Hmm. try to adapt
			value = [x.decode('utf-8') if isinstance(x, str) else x for x in value] # allow ascii strings for old app tests
			super(BodyFieldProperty, self).__set__( inst, tuple( (self._field.value_type.fromObject(x) for x in value ) ) )

		# Ownership (containment) and censoring are already taken care of by the
		# event listeners on IBeforeSequenceAssignedEvent


@interface.implementer(nti_interfaces.INote,
					    # requires annotations
					   nti_interfaces.ILikeable,
					   nti_interfaces.IFavoritable,
					   nti_interfaces.IFlaggable,
					   # provides annotations
					   an_interfaces.IAttributeAnnotatable )
class Note(ThreadableMixin,Highlight):
	"""
	Implementation of a note.
	"""

	#: A sequence of properties we would like to copy from the parent
	#: when a child reply is created. If the child already has them, they
	#: are left alone.
	#: This consists of the anchoring properties
	_inheritable_properties_ = ( 'applicableRange', 'title' )

	#: We override the default highlight style to suppress it.
	style = 'suppressed'

	body = BodyFieldProperty(nti_interfaces.INote['body']) # uses the 'body' in the dict, which is compatible with persistent objects

	title = FieldProperty(nti_interfaces.INote['title'])

	def __init__(self):
		super(Note,self).__init__()

	__getitem__ = _make_getitem( 'body' )

from .highlight import HighlightInternalObjectIO
from .threadable import ThreadableExternalizableMixin

@component.adapter(nti_interfaces.INote)
class NoteInternalObjectIO(ThreadableExternalizableMixin,HighlightInternalObjectIO):

	def _resolve_external_body( self, context, parsed, body ):
		"""
		Attempt to resolve elements in the body to existing canvas objects
		that are my children. If we find them, then update them in place
		to the best of our ability.
		"""
		note = self.context
		if not note or not note.body or note.body == ("",):
			# Our initial state. Empty body, nothing to resolve against.
			return body

		# Support raw body, not wrapped
		if isinstance(body, six.string_types ):
			body = [body]
		for i, item in enumerate(body):
			if not nti_interfaces.ICanvas.providedBy( item ):
				continue
			ext_val = getattr( item, '_v_updated_from_external_source', {} )
			if 'NTIID' not in ext_val:
				continue
			existing_canvas = find_object_with_ntiid( ext_val['NTIID'] )
			if getattr( existing_canvas, '__parent__', None ) is not note:
				continue
			# Ok, so we found one of my children. Update it in place
			__traceback_info__ = i, item, ext_val, existing_canvas, note
			update_from_external_object( existing_canvas, ext_val, context=context )
			existing_canvas.updateLastMod()
			body[i] = existing_canvas
		return body

	__external_resolvers__ = { 'body': _resolve_external_body }


	def toExternalObject( self, mergeFrom=None ):
		ext = super(NoteInternalObjectIO,self).toExternalObject(mergeFrom=mergeFrom)
		if ext['body'] in ( Note.body, [''], None ): # don't write out the base state, it confuses updating and isn't valid
			del ext['body']
		return ext

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		# Only updates to the body are accepted
		parsed.pop( 'text', None )

		super(NoteInternalObjectIO, self).updateFromExternalObject( parsed, *args, **kwargs )

		note = self.context

		# If we are newly created, and a reply, then
		# we want to use our policy settings to determine the sharing
		# of the new note. This is because our policy settings
		# may be user/community/context specific.
		if not note._p_mtime and note.inReplyTo:
			# Current policy is to copy the sharing settings
			# of the parent, and share back to the parent's creator,
			# only making sure not to share with ourself since that's weird
			# (Be a bit defensive about bad inReplyTo)
			if not hasattr( note.inReplyTo, 'sharingTargets' ): # pragma: no cover
				raise AttributeError( 'Illegal value for inReplyTo: %s' % note.inReplyTo )
			sharingTargets = set( note.inReplyTo.sharingTargets )
			sharingTargets.add( note.inReplyTo.creator )
			sharingTargets.discard( note.creator )
			sharingTargets.discard( None )

			note.updateSharingTargets( sharingTargets )


			# Now some other things we want to inherit if possible
			for copy in note._inheritable_properties_:
				val = getattr( note.inReplyTo, copy, getattr( note, copy, None ) )
				if val is not None:
					setattr( note, copy, val )
