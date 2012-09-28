#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with :mod:`z3c.table`. Contains some column support
classes.


$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import


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

class NoteBodyColumn(column.GetAttrColumn):
	"""
	Column to display the body of a Note.
	"""
	weight = 1
	header = 'Content'
	attrName = 'body'

	def renderCell( self, item ):
		content = super(NoteBodyColumn,self).renderCell( item )
		parts = []
		for part in content:
			if nti_interfaces.ICanvas.providedBy( part ):
				# TODO: Inspect about the presence of images, etc
				parts.append( "&lt;CANVAS OBJECT&gt;" )
			else:
				parts.append( frg_interfaces.IPlainTextContentFragment( part, None ) or unicode(part) )
		return '<br />'.join( parts )

class IntIdCheckBoxColumn(column.CheckBoxColumn):
	"""
	A selection column, meant to go first in a table, that selects items
	based on their globally registered value in :class:`zc.intid.IIntIds`.
	"""
	weight = 0
	header = 'Select'

	def getItemValue(self, item):
		return str(component.getUtility( zc_intid.IIntIds ).getId( item ))

def fake_dc_core_for_times( item ):
	times = dc_interfaces.IDCTimes( item, None )
	if times is None:
		return item # No values to proxy from, no point in doing so

	return _FakeDublinCoreProxy( times )


class CreatedColumn(column.CreatedColumn):
	"""
	Column to display the created time of any :class:`nti.dataserver.interfaces.ICreated`
	"""
	weight = 3
	def getSortKey( self, item ):
		return item.createdTime

	def renderCell(self, item):
		return super(CreatedColumn,self).renderCell( fake_dc_core_for_times( item ) )

class ModifiedColumn(column.ModifiedColumn):
	"""
	Column to display the modified time of any :class:`nti.dataserver.interfaces.ILastModified`
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

class UsernameColumn(column.GetAttrColumn):
	"""
	Displays a username
	"""
	header = 'Username'
	attrName = 'username'

class AdaptingGetAttrColumn(column.GetAttrColumn):
	"""
	Adapts first, then gets the arr.
	"""

	adapt_to = None

	def getValue( self, obj ):
		return super(AdaptingGetAttrColumn,self).getValue( self.adapt_to( obj, obj ) )
