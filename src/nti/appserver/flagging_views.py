#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to flagging and moderating flagged objects.


$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from pyramid.security import authenticated_userid
import pyramid.httpexceptions  as hexc
from pyramid.view import view_config

from zope import interface
from zope import component
from zc import intid as zc_intid

from nti.appserver import _util

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import flagging
from nti.dataserver import authorization as nauth

from nti.externalization import interfaces as ext_interfaces
from nti.contentfragments import interfaces as frg_interfaces

FLAG_VIEW = 'flag'
FLAG_AGAIN_VIEW = 'flag.metoo'
UNFLAG_VIEW = 'unflag'

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IFlaggable)
class FlagLinkDecorator(_util.AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate flag links. Note that once something is flagged,
	it remains so as far as normal users are concerned, until it is moderated.
	Thus the same view is used in both cases (but with slightly different names
	to let the UI know if something has already been flagged).
	"""
	false_view = FLAG_VIEW
	true_view = FLAG_AGAIN_VIEW
	predicate = staticmethod(flagging.flags_object)


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFlaggable,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name=FLAG_VIEW)
def _FlagView(request):
	"""
	Given an :class:`nti_interfaces.IFlaggable`, make the
	current user flag the object, and return it.

	Registered as a named view, so invoked via the @@flag syntax.

	"""

	flagging.flag_object( request.context, authenticated_userid( request ) )
	return _util.uncached_in_response( request.context )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFlaggable,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name=FLAG_AGAIN_VIEW)
def _FlagMeTooView(request):
	return _FlagView( request )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFlaggable,
			  permission=nauth.ACT_MODERATE,
			  request_method='POST',
			  name=UNFLAG_VIEW)
def _UnFlagView(request):
	"""
	Given an :class:`nti_interfaces.IFlaggable`, make the
	current user unflag the object, and return it. Unlike
	flagging, this view is protected with :const:`nti.dataserver.authorization.ACT_MODERATE` permissions.

	Registered as a named view, so invoked via the @@unflag syntax.

	"""

	flagging.unflag_object( request.context, authenticated_userid( request ) )
	return _util.uncached_in_response( request.context )

########
## Right here is code for a moderation view:
## There is a static template that views all
## flagged objects and presents two options: delete to remove the object,
## and 'unflag' to unflag the object. The view code will accept the POST of that
## form and take the appropriate actions.


from z3c.table import column, table
from zope.dublincore import interfaces as dc_interfaces
from zope.proxy.decorator import SpecificationDecoratorBase
from nti.appserver.z3c_zpt import PyramidZopeRequestProxy

@interface.implementer(dc_interfaces.IZopeDublinCore)
class _FakeDublinCoreProxy(SpecificationDecoratorBase):
	pass

def _moderation_table( request ):
	content = component.getUtility( nti_interfaces.IGlobalFlagStorage ).iterflagged()
	content = list(content)
	the_table = ModerationAdminTable( content,
									  PyramidZopeRequestProxy( request ) )

	the_table.update()
	return the_table

@view_config( route_name='objects.generic.traversal',
			  renderer='templates/moderation_admin.pt',
			  permission=nauth.ACT_MODERATE,
			  request_method='GET',
			  name='moderation_admin')
def moderation_admin( request ):
	return _moderation_table( request )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_MODERATE,
			  request_method='POST',
			  name='moderation_admin')
def moderation_admin_post( request ):
	the_table = _moderation_table( request )

	if 'subFormTable.buttons.unflag' in request.POST:
		for item in the_table.selectedItems:
			flagging.unflag_object( item, authenticated_userid( request ) )
	elif 'subFormTable.buttons.delete' in request.POST:
		# TODO: We should probably do something in this objects place,
		# notify the user they have been moderated. As it is, the object
		# silently disappears
		for item in the_table.selectedItems:
			with item.creator.updates():
				item.creator.deleteContainedObject( item.containerId, item.id )

	# Else, no action.
	# Redisplay the page with a get request to avoid the "re-send this POST?" problem
	get_path = request.path  + (('?' + request.query_string) if request.query_string else '')
	return hexc.HTTPFound(location=get_path)


class ModerationAdminTable(table.SequenceTable):
	pass

@component.adapter(None,None,ModerationAdminTable)
class NoteBodyColumn(column.GetAttrColumn):
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
				parts.append( frg_interfaces.IPlainTextContentFragment( part ) )
		return '<br />'.join( parts )

class IntIdCheckBoxColumn(column.CheckBoxColumn):
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
	weight = 3
	def getSortKey( self, item ):
		return item.createdTime

	def renderCell(self, item):
		return super(CreatedColumn,self).renderCell( fake_dc_core_for_times( item ) )

class ModifiedColumn(column.ModifiedColumn):
	weight = 4

	def getSortKey( self, item ):
		return item.lastModified

	def renderCell(self, item):
		return super(ModifiedColumn,self).renderCell( fake_dc_core_for_times( item ) )

class CreatorColumn(column.GetAttrColumn):
	weight = 10
	header = 'Creator'
	attrName = 'creator'
