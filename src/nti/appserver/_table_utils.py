#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with :mod:`z3c.table`. Contains some column support
classes.


$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
logger = __import__('logging').getLogger(__name__)
import cgi
from collections import Counter

from zope import interface
from zope import component
from zc import intid as zc_intid


from nti.dataserver import interfaces as nti_interfaces
from nti.contentfragments import interfaces as frg_interfaces
import pyramid.interfaces
import z3c.table.interfaces

from z3c.table import column
from zope.dublincore import interfaces as dc_interfaces
from zope.proxy.decorator import SpecificationDecoratorBase

from zope.traversing.browser.interfaces import IAbsoluteURL

from nti.dataserver.links_external import render_link
from nti.ntiids import ntiids
from pyramid import traversal

@interface.implementer(dc_interfaces.IZopeDublinCore)
class _FakeDublinCoreProxy(SpecificationDecoratorBase):
	pass

@interface.implementer(IAbsoluteURL)
@component.adapter(z3c.table.interfaces.ITable, pyramid.interfaces.IRequest)
class TrivialTableAbsoluteURL(object):
	"""
	Needed to be able to produce the batching URLs.
	"""
	def __init__( self, context, request ):
		self.context = context
		self.request = request

	def __call__( self ):
		return self.request.path

class NoteLikeBodyColumn(column.GetAttrColumn):
	"""
	Column to display the ``body`` of a :class:`nti.dataserver.interfaces.INote`
	(or something similar, such as a chat message).
	"""
	weight = 1
	header = 'Content'
	attrName = 'body'
	cssClasses = { 'td': 'content-body' }
	defaultValue = ()

	def renderCell( self, item ):
		content = super(NoteLikeBodyColumn,self).renderCell( item )
		if content is self.defaultValue:
			# TODO: These hacks are starting to get out of hand.
			# Need to seriously investigate the zope contentprovider concepts
			# See also feed_views.py
			# This hack is for forum entries
			headline = getattr( item, 'headline', None )
			if headline:
				content = getattr( headline, 'body', self.defaultValue )
				content = list( content )
				content.insert( 0, getattr( headline, 'title', '' ) )

		parts = []
		for part in content or ():
			if nti_interfaces.ICanvas.providedBy( part ):
				# TODO: We can do better than this. For one, we could use adapters
				body = ["<div class='canvas'>&lt;CANVAS OBJECT of length %s&gt;" % len(part)]
				part_types = Counter()
				for canvas_part in part:
					part_types[type(canvas_part).__name__] += 1
					if hasattr( canvas_part, 'url' ):
						# Write it out as a link to the image.
						# TODO: This is a bit of a hack
						# TODO: Are there any permissions problems with this? Potentially?
						# The data-url wouldn't have them. In notification emails, this
						# could also be a problem
						part_ext = canvas_part.toExternalObject()
						__traceback_info__ = part_ext
						link = part_ext['url']
						# TODO: Apparently there are some unmigrated objects that don't have _file
						# hidden away somewhere?
						link_external = render_link(link) if nti_interfaces.ILink.providedBy( link ) else link
						body.append( "<img src='%s' />" % link_external )
					elif hasattr( canvas_part, 'text' ):
						body.append( cgi.escape( canvas_part.text ) )
				for name, cnt in part_types.items():
					body.append( "&lt;%d %ss&gt;" % (cnt, name) )
				body.append( '</div>' )
				parts.append( '<br />'.join( body ) )
			elif part:
				parts.append( frg_interfaces.IPlainTextContentFragment( part, None ) or unicode(part) )
		return '<div>' + '<br />'.join( parts ) + self._render_suffix(item) + '</div>'

	def _render_suffix( self, item ):
		# hack for rendering MessageInfo objects to add recipient information.
		# If we add more of these we need to do something with ZCA
		recip = getattr( item, 'recipients', None )
		if recip:
			return "<br /><span class='chat-recipients'>(Recipients: " + ' '.join( recip ) + ')</span>'

		return ''

class IntIdCheckBoxColumn(column.CheckBoxColumn):
	"""
	A selection column, meant to go first in a table, that selects items
	based on their globally registered value in :class:`zc.intid.IIntIds`.
	"""
	weight = 0
	header = 'Select'
	cssClasses = { 'td': 'select-object-checkbox' }

	def getItemValue(self, item):
		return str(component.getUtility( zc_intid.IIntIds ).queryId( item ) or -1)

def fake_dc_core_for_times( item ):
	times = dc_interfaces.IDCTimes( item, None )
	if times is None:
		return item # No values to proxy from, no point in doing so
	if dc_interfaces.IZopeDublinCore.providedBy( times ):
		return times
	return _FakeDublinCoreProxy( times )

# TODO: Make Created and Modified column work for nti.dataserver.interfaces.ICreated/ILastModified
# That, or finally remove those interfaces
class CreatedColumn(column.CreatedColumn):
	"""
	Column to display the created time of any :class:`zope.dublincore.interfaces.IDCTimes`
	"""
	weight = 3
	def getSortKey( self, item ):
		return item.createdTime

	def renderCell(self, item):
		return super(CreatedColumn,self).renderCell( fake_dc_core_for_times( item ) )

class ModifiedColumn(column.ModifiedColumn):
	"""
	Column to display the modified time of any :class:`zope.dublincore.interfaces.IDCTimes`
	"""

	weight = 4

	def getSortKey( self, item ):
		return item.lastModified

	def renderCell(self, item):
		return super(ModifiedColumn,self).renderCell( fake_dc_core_for_times( item ) )

class CreatorColumn(column.GetAttrColumn):
	"""
	Column to display the creator of any :class:`nti.dataserver.interfaces.ICreated`.
	"""
	weight = 10
	header = 'Creator'
	attrName = 'creator'

class KindColumn(column.GetAttrColumn):
	"""
	Column to display the kind of an object.
	"""

	weight = 11
	header = 'Kind'
	attrName = 'mimeType'


class ContainerColumn(column.GetAttrColumn):
	"""
	Column to display the container ID of a column.
	"""

	weight = 12
	header = 'ContainerID'
	attrName = 'containerId'

	def getValue( self, obj ):
		container_id = super(ContainerColumn,self).getValue( obj )
		if container_id:
			try:
				container = ntiids.find_object_with_ntiid( container_id )
				container_name = getattr( container, '__name__', self.defaultValue )
				if ntiids.is_valid_ntiid_string( container_name ):
					# OK, probably somewhere down in userdata. This is probably not helpful
					# It could also be an assessment question, NAQ, but those currently do
					# not have valid __parent__ attributes, sadly
					return self.defaultValue
				# Try to make it into a path
				try:
					return '/'.join(traversal.resource_path_tuple( container ))
				except (AttributeError, KeyError, ValueError):
					return container_name
			except (ValueError, KeyError, AttributeError):
				return self.defaultValue
		return self.defaultValue

class UsernameColumn(column.GetAttrColumn):
	"""
	Displays a username
	"""
	header = 'Username'
	attrName = 'username'

class AdaptingGetAttrColumn(column.GetAttrColumn):
	"""
	Adapts first, then gets the attribute.
	"""

	adapt_to = None

	def getValue( self, obj ):
		return super(AdaptingGetAttrColumn,self).getValue( self.adapt_to( obj, obj ) )
