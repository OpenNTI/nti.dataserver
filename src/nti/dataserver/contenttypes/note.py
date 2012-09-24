#!/usr/bin/env python
"""
Definition of the Note object.
"""
from __future__ import print_function, unicode_literals

import six

from nti.dataserver import interfaces as nti_interfaces


from nti.contentfragments import interfaces as frg_interfaces
from nti.contentfragments import censor

from nti.ntiids.ntiids import find_object_with_ntiid

from zope import interface

from zope import component
from ZODB.interfaces import IConnection
from zope.annotation import interfaces as an_interfaces
from zope.container.contained import contained
import zope.schema.interfaces

from .highlight import Highlight
from .threadable import ThreadableExternalizableMixin
from .base import _make_getitem

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

	__getitem__ = _make_getitem( 'body' )

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(Note,self).toExternalDictionary(mergeFrom=mergeFrom)
		# In our initial state, don't try to send empty body/text
		if self.body == ('',):
			result.pop( 'body' )

		return result

	def _resolve_external_body( self, context, parsed, body ):
		"""
		Attempt to resolve elements in the body to existing canvas objects
		that are my children. If we find them, then update them in place
		to the best of our ability.
		"""
		if not self.body or self.body == ("",):
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
			if getattr( existing_canvas, '__parent__', None ) != self:
				continue
			# Ok, so we found one of my children. Update it in place
			existing_canvas.updateFromExternalObject( ext_val, context=context )
			existing_canvas.updateLastMod()
			body[i] = existing_canvas
		return body

	__external_resolvers__ = { 'body': _resolve_external_body }

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
			if not self.body:
				raise zope.schema.interfaces.RequiredMissing('Must supply body')

			# Verify that the body contains supported types, if
			# sent from the client.
			for i, x in enumerate(self.body):
				__traceback_info__ = i, x
				if not isinstance( x, basestring) and not nti_interfaces.ICanvas.providedBy( x ):
					raise zope.schema.interfaces.WrongContainedType()
				if isinstance( x, basestring ) and len(x) == 0:
					raise zope.schema.interfaces.TooShort()
				if nti_interfaces.ICanvas.providedBy( x ):
					contained( x, self, unicode(i) )
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
				x = censor.censor_assign(x, self, 'body' )
				return x

			self.body = [_sanitize(x) for x in self.body]

			# convert mutable lists to immutable tuples
			self.body = tuple( self.body )


		# If we are newly created, and a reply, then
		# we want to use our policy settings to determine the sharing
		# of the new note. This is because our policy settings
		# may be user/community/context specific.
		if not self._p_mtime and self.inReplyTo:
			# Current policy is to copy the sharing settings
			# of the parent, and share back to the parent's creator,
			# only making sure not to share with ourself since that's weird
			# (Be a bit defensive about bad inReplyTo)
			if not hasattr( self.inReplyTo, 'sharingTargets' ): # pragma: no cover
				raise AttributeError( 'Illegal value for inReplyTo: %s' % self.inReplyTo )
			sharingTargets = set( self.inReplyTo.sharingTargets )
			sharingTargets.add( self.inReplyTo.creator )
			sharingTargets.discard( self.creator )
			sharingTargets.discard( None )

			self.updateSharingTargets( sharingTargets )


			# Now some other things we want to inherit if possible
			for copy in self._inheritable_properties_:
				val = getattr( self.inReplyTo, copy, getattr( self, copy, None ) )
				if val is not None:
					setattr( self, copy, val )
