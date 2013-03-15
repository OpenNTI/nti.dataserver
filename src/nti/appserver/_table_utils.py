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
from abc import ABCMeta #, abstractmethod

from zope import interface
from zope import component
from zc import intid as zc_intid


from nti.dataserver import interfaces as nti_interfaces
from nti.contentfragments import interfaces as frg_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
import pyramid.interfaces
import z3c.table.interfaces
from zope.contentprovider import interfaces as cp_interfaces

from z3c.table import column
from zope.dublincore import interfaces as dc_interfaces
from zope.proxy.decorator import SpecificationDecoratorBase

from zope.traversing.browser.interfaces import IAbsoluteURL

from nti.dataserver.links_external import render_link
from nti.ntiids import ntiids
from pyramid import traversal
from zope.contentprovider.provider import ContentProviderBase

import html5lib
from html5lib import treebuilders
import lxml.etree

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
		content_provider = component.queryMultiAdapter( (item, self.request, self),
														cp_interfaces.IContentProvider )
		if content_provider:
			content_provider.update()
			return content_provider.render()
		return ''

class AbstractNoteContentProvider(ContentProviderBase):
	"""
	Base content provider for something that is note-like
	(being modeled content and typically having a body that is a :func:`nti.dataserver.interfaces.CompoundModeledContentBody`).
	"""
	__metaclass__ = ABCMeta

	def get_body_parts(self):
		return self.context.body

	def render_body_part( self, part ):
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
			return '<br />'.join( body )

		if frg_interfaces.IHTMLContentFragment.providedBy( part ):
			parser = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
			doc = parser.parse( part )
			body = doc.find('body')
			if body is not None:
				part = lxml.etree.tostring( body, method='html', encoding=unicode )
				result = part[6:-7] # strip the enclosing body tag
			else:
				result = ''
		else:
			result = frg_interfaces.IPlainTextContentFragment( part, None ) or unicode(part)
		return result

	def update(self):
		pass

	def render_prefix(self):
		return ''
	def render_suffix(self):
		return ''

	def render(self):
		parts = []
		parts.append( '<div>' )
		parts.append( self.render_prefix() )
		for part in self.get_body_parts():
			rendered = self.render_body_part( part )
			if rendered:
				parts.append( '<br />' )
				parts.append( rendered )

		parts.append( self.render_suffix() )

		return ''.join( parts )

@interface.implementer(cp_interfaces.IContentProvider)
@component.adapter(nti_interfaces.INote, interface.Interface, NoteLikeBodyColumn)
class NoteContentProvider(AbstractNoteContentProvider):
	pass

@interface.implementer(cp_interfaces.IContentProvider)
@component.adapter(chat_interfaces.IMessageInfo, interface.Interface, NoteLikeBodyColumn)
class MessageInfoContentProvider(AbstractNoteContentProvider):

	def get_body_parts(self):
		return self.context.body

	def render_suffix(self):
		recip = getattr( self.context, 'recipients', None )
		if recip:
			return "<br /><span class='chat-recipients'>(Recipients: " + ' '.join( recip ) + ')</span>'
		return ''

@interface.implementer(cp_interfaces.IContentProvider)
@component.adapter(frm_interfaces.IHeadlineTopic, interface.Interface, NoteLikeBodyColumn)
class HeadlineTopicContentProvider(AbstractNoteContentProvider):

	def get_body_parts(self):
		return self.context.headline.body

	def render_prefix(self):
		return self.context.headline.title

@interface.implementer(cp_interfaces.IContentProvider)
@component.adapter(frm_interfaces.IPersonalBlogComment, interface.Interface, NoteLikeBodyColumn)
class PersonalBlogCommentContentProvider(AbstractNoteContentProvider):
	pass


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
