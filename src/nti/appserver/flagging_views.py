#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to flagging and moderating flagged objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import component
from zope import interface

from zc import intid as zc_intid

from pyramid.request import Request
from pyramid.view import view_config
from pyramid.interfaces import IRequest
from pyramid import httpexceptions as hexc

from nti.app.renderers.caching import uncached_in_response
from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator
from nti.app.renderers.interfaces import IPreRenderResponseCacheController

from nti.dataserver import flagging

from nti.dataserver.interfaces import IFlaggable
from nti.dataserver.interfaces import IGlobalFlagStorage

from nti.dataserver import authorization as nauth

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.internalization import update_from_external_object

from .interfaces import IModeratorDealtWithFlag  # BWC export

FLAG_VIEW = 'flag'
UNFLAG_VIEW = 'unflag'
FLAG_AGAIN_VIEW = 'flag.metoo'

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IFlaggable, IRequest)
class FlagLinkDecorator(AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate flag links. Note that once something is flagged,
	it remains so as far as normal users are concerned, until it is moderated.
	Thus the same view is used in both cases (but with slightly different names
	to let the UI know if something has already been flagged).
	"""
	false_view = FLAG_VIEW
	true_view = FLAG_AGAIN_VIEW
	link_predicate = staticmethod(flagging.flags_object)

	def _predicate(self, context, mapping):
		# Flagged and handled once. Cannot be flagged again. This
		# is only used on IMessageInfo objects which are otherwise
		# immutable. TODO: This probably needs handled differently.
		return self._is_authenticated and not IModeratorDealtWithFlag.providedBy(context)

def _do_flag(f, request):
	try:
		f(request.context, request.authenticated_userid)
		return uncached_in_response(request.context)
	except KeyError:  # pragma: no cover
		logger.warn("Attempting to un/flag something not found. Was it deleted and the link is stale? %s",
					request.context, exc_info=True)
		raise hexc.HTTPNotFound()

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IFlaggable,
			 permission=nauth.ACT_READ,  # anyone logged in...
			 request_method='POST',
			 name=FLAG_VIEW)
def _FlagView(request):
	"""
	Given an :class:`.IFlaggable`, make the
	current user flag the object, and return it.

	Registered as a named view, so invoked via the @@flag syntax.

	"""
	return _do_flag(flagging.flag_object, request)

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IFlaggable,
			 permission=nauth.ACT_READ,  # anyone logged in...
			 request_method='POST',
			 name=FLAG_AGAIN_VIEW)
def _FlagMeTooView(request):
	return _FlagView(request)

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IFlaggable,
			 permission=nauth.ACT_MODERATE,
			 request_method='POST',
			 name=UNFLAG_VIEW)
def _UnFlagView(request):
	"""
	Given an :class:`IFlaggable`, make the
	current user unflag the object, and return it. Unlike
	flagging, this view is protected with 
	:const:`nti.dataserver.authorization.ACT_MODERATE` permissions.

	Registered as a named view, so invoked via the @@unflag syntax.

	"""
	return _do_flag(flagging.unflag_object, request)

########
# Right here is code for a moderation view:
# There is a static template that views all
# flagged objects and presents two options: delete to remove the object,
# and 'unflag' to unflag the object. The view code will accept the POST of that
# form and take the appropriate actions.

from zope.publisher.interfaces.browser import IBrowserRequest

from z3c.table import table

from .ugd_query_views import lists_and_dicts_to_ext_collection

def _moderation_table(request):
	intids = component.getUtility(zc_intid.IIntIds)
	content = list(component.getUtility(IGlobalFlagStorage).iterflagged())
	content_dict = lists_and_dicts_to_ext_collection((content,),
													 predicate=intids.queryId, 
													 ignore_broken=True)

	IPreRenderResponseCacheController(content_dict)(content_dict, 
													{'request': request})
	content = content_dict['Items']

	the_table = ModerationAdminTable(content,
									  IBrowserRequest(request))

	the_table.update()
	return the_table

@view_config(route_name='objects.generic.traversal',
			 renderer='templates/moderation_admin.pt',
			 permission=nauth.ACT_MODERATE,
			 request_method='GET',
			 name='moderation_admin')
def moderation_admin(request):
	return _moderation_table(request)

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_MODERATE,
			 request_method='POST',
			 name='moderation_admin')
def moderation_admin_post(request):
	the_table = _moderation_table(request)

	if 'subFormTable.buttons.unflag' in request.POST:
		for item in the_table.selectedItems:
			flagging.unflag_object(item, request.authenticated_userid)
	elif 'subFormTable.buttons.delete' in request.POST:
		# TODO: We should probably do something in this object's place,
		# notify the user they have been moderated. As it is, the object
		# silently disappears.
		# Rather than deleting, we could add an interface (IModeratorDealtWithFlag)
		# but somehow we need to be able to both present it differently to the end user,
		# and know that it is the result of moderator action (so it can go into
		# statistics and so on), and remove it from search indexes. If we do this, then we probably need to
		# make the item immutable from external users, or clear this flag
		# on mutation. Or something.
		# Also if we do this, do we want to remove its 'public' visibility? Or for the sake of
		# threads do we need to leave it?
		for item in the_table.selectedItems:
			flagging.unflag_object(item, request.authenticated_userid)
			interface.alsoProvides(item, IModeratorDealtWithFlag)  # TODO: Apply the IDeletedObjectPlaceholder ?

			# TODO: This is not very generic due to the way that
			# chat transcripts are currently being stored. Furthermore,
			# it's quite probable that doing something with the chat message
			# is not properly updating indexes for this same reason; in particular,
			# we have no way to recapture the complete set of recipients that got the
			# message due to shadowing, etc

			# Run the default 'DELETE' action for the complete path to this object
			# by invoking it as a request. It this way, we get to dispatch based on the
			# type of object automatically, so long as it has a DELETE action
			subrequest = Request.blank('/dataserver2/Objects/' + to_external_ntiid_oid(item))
			subrequest.method = 'DELETE'
			# Impersonate the creator of the object to get the right permissions.
			# in this way, ACT_MODERATE automatically implies ACT_DELETE.
			# TODO: We could also use the nti.dataserver.authentication policy?
			creator = item.creator.username if hasattr(item.creator, 'username') else item.creator
			subrequest.environ['REMOTE_USER'] = creator
			subrequest.environ['repoze.who.identity'] = {'repoze.who.userid': creator}
			subrequest.possible_site_names = request.possible_site_names
			try:
				request.invoke_subrequest(subrequest)  # Don't use tweens, run in same site, same transaction
			except (hexc.HTTPForbidden, hexc.HTTPMethodNotAllowed):  # What else to catch?
				del_item = None
				try:
					del_item = item.creator.deleteContainedObject(item.containerId, item.id)
				except AttributeError:
					pass

				if del_item is None:
					# OK, even its user cannot delete it. At least we can try to update its
					# 'body' property. This is probably a chat message
					update_from_external_object(item, 
							{'body': [_("This item has been deleted by the moderator.")] })
					logger.warn("Failed to delete moderated item %s", item)

	# Else, no action.
	# Redisplay the page with a get request to avoid the "re-send this POST?" problem
	get_path = request.path + (('?' + request.query_string) if request.query_string else '')
	return hexc.HTTPFound(location=get_path)

class ModerationAdminTable(table.SequenceTable):
	pass
