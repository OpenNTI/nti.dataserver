#!/usr/bin/env python
"""
Definition of the Note object.
"""
from __future__ import print_function, unicode_literals

import six

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.internalization import update_from_external_object
from nti.contentfragments import interfaces as frg_interfaces
from nti.contentfragments import censor

from nti.ntiids.ntiids import find_object_with_ntiid

from zope import component
from zope import interface

from ZODB.interfaces import IConnection
from zope.annotation import interfaces as an_interfaces
from zope.container.contained import contained
import zope.schema.interfaces

from .highlight import Highlight
from .threadable import ThreadableMixin
from .base import _make_getitem

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
	_inheritable_properties_ = ( 'applicableRange', )

	#: We override the default highlight style to suppress it.
	style = 'suppressed'

	#: The default body consists of one empty string
	body = ("",)

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
		if not note or note.body == ("",):
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

	def _update_body( self, note, body ):
		# Support text and body as input
		# Support raw body, not wrapped
		if isinstance( body, six.string_types ):
			body = ( body, )

		if not body:
			raise zope.schema.interfaces.RequiredMissing('Must supply body')

		# Verify that the body contains supported types, if
		# sent from the client.
		for i, x in enumerate(body):
			__traceback_info__ = i, x
			if not isinstance(x, basestring) and not nti_interfaces.ICanvas.providedBy( x ):
				raise zope.schema.interfaces.WrongContainedType()
			if isinstance( x, basestring ) and len(x) == 0:
				raise zope.schema.interfaces.TooShort()
			if nti_interfaces.ICanvas.providedBy( x ):
				contained( x, note, unicode(i) )
				jar = IConnection( x, None )
				if jar and not getattr( x, '_p_oid', None ): # If we have a connection, make sure the canvas does too
					jar.add( x )


		# Sanitize the body. Anything that can become a fragment, do so, incidentally
		# sanitizing and censoring it along the way.
		def _sanitize(x):
			if frg_interfaces.IHTMLContentFragment.providedBy( x ) and not frg_interfaces.ISanitizedHTMLContentFragment.providedBy( x ):
				x = frg_interfaces.ISanitizedHTMLContentFragment( x )
			else:
				x = frg_interfaces.IUnicodeContentFragment( x, x )
			x = censor.censor_assign(x, note, 'body' )
			return x

		# convert mutable lists to immutable tuples
		note.body = tuple( [_sanitize(x) for x in body] )

	def toExternalObject( self ):
		ext = super(NoteInternalObjectIO,self).toExternalObject()
		if ext['body'] in ( Note.body, [''] ): # don't write out the base state, it confuses updating
			del ext['body']
		return ext

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		# Only updates to the body are accepted
		parsed.pop( 'text', None )

		body = parsed.pop( 'body', self )
		super(NoteInternalObjectIO, self).updateFromExternalObject( parsed, *args, **kwargs )

		note = self.context
		__traceback_info__ = note, body, parsed
		if body is not self:
			self._update_body( note, body )

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
