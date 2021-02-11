#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with :mod:`z3c.table`. Contains some column support
classes.

.. note:: It is critical for the columns you use in a table to have distinct
	`weight` values; if they don't, their order might vary across machines as ties
	are broken based on the arbitrary iteration order of dicts-of-dicts.
	Alternately, you can override `orderColumns` in your table subclass.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import cgi
from abc import ABCMeta #, abstractmethod
from collections import Counter

from lxml import etree

import html5lib
from html5lib import treebuilders

from zope import component
from zope import interface

from zope.contentprovider.interfaces import IContentProvider
from zope.contentprovider.provider import ContentProviderBase

from zope.dublincore.interfaces import IDCTimes
from zope.dublincore.interfaces import IZopeDublinCore

from zope.intid import IIntIds

from zope.proxy.decorator import SpecificationDecoratorBase

from zope.traversing.browser.interfaces import IAbsoluteURL

import z3c.table.interfaces
from z3c.table import column

import pyramid.interfaces
from pyramid import traversal

from nti.chatserver.interfaces import IMessageInfo

from nti.contentfragments.interfaces import IHTMLContentFragment
from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.interfaces import ILink
from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import ICanvas
from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic

from nti.links.externalization import render_link

from nti.ntiids import ntiids

@interface.implementer(IZopeDublinCore)
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
														IContentProvider )
		if content_provider:
			content_provider.update()
			return content_provider.render()
		return ''

class AbstractNoteContentProvider(ContentProviderBase):
	"""
	Base content provider for something that is note-like
	(being modeled content and typically having a body that is a
	:func:`nti.dataserver.interfaces.CompoundModeledContentBody`).
	"""
	__metaclass__ = ABCMeta

	def get_body_parts(self):
		return self.context.body

	def render_body_part( self, part ):
		if ICanvas.providedBy( part ):
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
					link_external = render_link(link) if ILink.providedBy( link ) else link
					body.append( "<img src='%s' />" % link_external )
				elif hasattr( canvas_part, 'text' ):
					body.append( cgi.escape( canvas_part.text ) )
			for name, cnt in part_types.items():
				body.append( "&lt;%d %ss&gt;" % (cnt, name) )
			body.append( '</div>' )
			return '<br />'.join( body )

		if IHTMLContentFragment.providedBy( part ):
			parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("lxml"),
										 namespaceHTMLElements=False )
			doc = parser.parse( part )
			body = doc.find('body')
			if body is not None:
				part = getattr(etree ,'tostring')( body, method='html', encoding=unicode )
				result = part[6:-7] # strip the enclosing body tag
			else:
				result = ''
		else:
			result = IPlainTextContentFragment( part, None ) or unicode(part)
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
		for part in self.get_body_parts() or tuple():
			rendered = self.render_body_part( part )
			if rendered:
				parts.append( '<br />' )
				parts.append( rendered )

		parts.append( self.render_suffix() )
		parts.append( '</div>' )
		return ''.join( parts )

@interface.implementer(IContentProvider)
@component.adapter(INote, interface.Interface, NoteLikeBodyColumn)
class NoteContentProvider(AbstractNoteContentProvider):

	def render_prefix(self):
		if self.context.title:
			return '<span style="font-weight: bold">' + self.context.title + '</span>'
		return ''

@interface.implementer(IContentProvider)
@component.adapter(IMessageInfo, interface.Interface, NoteLikeBodyColumn)
class MessageInfoContentProvider(AbstractNoteContentProvider):

	def get_body_parts(self):
		return self.context.body

	def render_suffix(self):
		recip = getattr( self.context, 'recipients', None )
		if recip:
			return "<br /><span class='chat-recipients'>(Recipients: " + ' '.join( recip ) + ')</span>'
		return ''

@interface.implementer(IContentProvider)
@component.adapter(IHeadlineTopic, interface.Interface, NoteLikeBodyColumn)
class HeadlineTopicContentProvider(AbstractNoteContentProvider):

	def get_body_parts(self):
		return self.context.headline.body

	def render_prefix(self):
		return self.context.headline.title

@interface.implementer(IContentProvider)
@component.adapter(IPost, interface.Interface, NoteLikeBodyColumn)
class TopicCommentContentProvider(AbstractNoteContentProvider):
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
		return str(component.getUtility( IIntIds ).queryId( item ) or -1)

def fake_dc_core_for_times( item ):
	times = IDCTimes( item, None )
	if times is None:
		return item # No values to proxy from, no point in doing so
	if IZopeDublinCore.providedBy( times ):
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
	weight = 2

class AdaptingGetAttrColumn(column.GetAttrColumn):
	"""
	Adapts first, then gets the attribute.
	"""

	adapt_to = None

	def getValue( self, obj ):
		return super(AdaptingGetAttrColumn,self).getValue( self.adapt_to( obj, obj ) )
