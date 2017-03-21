#!/usr/bin/env python
"""
Defines traversal views and resources for the dataserver.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.location.location import LocationProxy

from zope.traversing.interfaces import IPathAdapter

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.authentication import get_remote_user as _get_remote_user

from nti.app.base.abstract_views import AbstractView
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.appserver import httpexceptions as hexc

from nti.appserver.context_providers import get_joinable_contexts

from nti.appserver.pyramid_authorization import is_readable

from nti.appserver.workspaces.interfaces import IService
from nti.appserver.workspaces.interfaces import ICollection

from nti.coremetadata.interfaces import UNAUTHENTICATED_PRINCIPAL_NAME

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IPrincipal
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS

def _service_for_user(user):
	if not user:
		user = IPrincipal(UNAUTHENTICATED_PRINCIPAL_NAME)

	# JAM: We should make this a multi-adapter on the request
	# so that the request can be threaded down through workspaces,
	# collections, etc.
	service = IService(user)
	return service

@interface.implementer(IPathAdapter)
def _service_path_adapter(context, request):
	user = _get_remote_user(request)
	return _service_for_user(user)

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_READ,
			 context=IService)
class _ServiceView(AbstractView):

	def __call__(self):
		return self.context

# TODO: Once we verify clients aren't referencing /dataserver2
# directly we should remove this in place of the /dataserver2/service
# path
class _ServiceGetView(AbstractAuthenticatedView):

	def __call__(self):
		return _service_for_user(self.remoteUser)

@view_defaults(route_name='objects.generic.traversal',
			   permission=nauth.ACT_READ,
			   renderer='rest',
			   request_method='GET')
class GenericGetView(AbstractView):

	def __call__(self):
		# TODO: We sometimes want to change the interface that we return
		# We're doing this to turn a dataserver IContainer (which externalizes poorly)
		# to an ICollection (which externalizes nicely.) How to make this
		# configurable/generic?
		# For right now, we're looking for an adapter registered with the name of the
		# last component we traversed, and then falling back to the default

		# TODO: Assuming the result that we get is some sort of container,
		# then we're leaving the renderer to insert next/prev first/last related
		# links and handle paging. Is that right?
		# NOTE: We'll take either one of the wrapper classes defined
		# in this module, or the object itself
		resource = getattr(self.request.context, 'resource', self.request.context)

		if IDeletedObjectPlaceholder.providedBy(resource):
			# For deleted objects, we want to return a 404 with our
			# deleted object placeholder in the payload.
			self.request.response.status = 404

		result = component.queryAdapter(resource,
										ICollection,
										name=self.request.traversed[-1])
		if not result:
			result = component.queryAdapter(resource,
											ICollection,
											default=resource)
		if hasattr(result, '__parent__'):
			# FIXME: Choosing which parent to set is also borked up.
			# Some context objects (resources) are at the same conceptual level
			# as the actual request.context, some are /beneath/ that level??
			# If we have a link all the way back up to the root, we're good?
			# TODO: This can probably mostly go away now?
			if result is resource:
				# Must be careful not to modify the persistent object
				result = LocationProxy(result,
									   getattr(result, '__parent__', None),
									   getattr(result, '__name__', None))

			if getattr(resource, '__parent__', None) is not None:
				result.__parent__ = resource.__parent__
				# FIXME: Another hack at getting the right parent relationship in.
				# The actual parent relationship is to the Provider object,
				# but it has no way back to the root resource. This hack is deliberately
				# kept very specific for now.
				if 	self.request.traversed[-1] == 'Classes' and \
					self.request.traversed[0] == 'providers':
					result.__parent__ = self.request.context.__parent__
				elif self.request.traversed[-1] == 'Pages' and \
					 self.request.traversed[0] == 'users':
					result.__parent__ = self.request.context.__parent__
			elif resource is not self.request.context and \
				 hasattr(self.request.context, '__parent__'):
				result.__parent__ = self.request.context.__parent__
		return result
_GenericGetView = GenericGetView #BWC

class _EmptyContainerGetView(AbstractView):

	def __call__(self):
		raise hexc.HTTPNotFound(self.request.context.ntiid)

def _method_not_allowed(request):
	raise hexc.HTTPMethodNotAllowed()

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 request_method='GET',
			 name='forbidden_related_context')
def _forbidden_related_context(context, request):
	# Reject anonymous access...and for BWC with old behaviour,
	# reject if you can rightfully access the context
	if not request.authenticated_userid or is_readable(context):
		raise hexc.HTTPForbidden()

	result = LocatedExternalDict()
	result.__parent__ = context
	result.__name__ = request.view_name

	results = get_joinable_contexts(context)
	if results:
		result[ITEMS] = results
	return result
