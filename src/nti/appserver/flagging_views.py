#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to flagging and moderating flagged objects.


$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from pyramid.security import authenticated_userid

from pyramid.view import view_config

from zope import interface
from zope import component

from nti.appserver import _util

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import flagging
from nti.dataserver import authorization as nauth

from nti.externalization import interfaces as ext_interfaces

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
## Right here would go
## code for a moderation view: There should be a static template that views all
## flagged objects and presents two checkboxes: delete to remove the object,
## and 'unflag' to unflag the object. The view code will accept the POST of that
## form and take the appropriate actions.

@view_config( route_name='objects.generic.traversal',
			  renderer='templates/moderation_admin.pt',
			  permission=nauth.ACT_MODERATE,
			  request_method='GET',
			  name='moderation_admin')
def moderation_admin( request ):
	# Seems chameleon/tal can't repeat on a generator/iterator?
	the_table = ModerationAdminTable( component.getUtility( nti_interfaces.IGlobalFlagStorage ).iterflagged(),
									  request )
	the_table.update()

	return the_table

from z3c.table import column, table
from zope.dublincore import interfaces as dc_interfaces
from zope.proxy import ProxyBase


class ModerationAdminTable(table.SequenceTable):
	pass

@component.adapter(None,None,ModerationAdminTable)
class NoteBodyColumn(column.GetAttrColumn):

	header = 'Content'
	attrName = 'body'

	def renderCell( self, item ):
		content = super(NoteBodyColumn,self).renderCell( item )
		return ''.join( content )

def fake_dc_core_for_times( item ):
	times = dc_interfaces.IDCTimes( item, None )
	if times is None:
		return item

	times = ProxyBase( times )
	interface.alsoProvides( times, dc_interfaces.IZopeDublinCore )
	return times


class CreatedColumn(column.CreatedColumn):
	def renderCell(self, item):
		return super(CreatedColumn,self).renderCell( fake_dc_core_for_times( item ) )

class ModifiedColumn(column.ModifiedColumn):
	def renderCell(self, item):
		return super(ModifiedColumn,self).renderCell( fake_dc_core_for_times( item ) )
