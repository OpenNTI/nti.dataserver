#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions having to do specifically with traversal in the context
of Pyramid. Many of these exist for legacy purposes to cause the existing
code to work with the newer physical resource tree.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import six
import collections

from zope import component
from zope import interface

from zope.location.interfaces import ILocation
from zope.location.interfaces import LocationError

from zope.security.management import queryInteraction

from zope.traversing.interfaces import IPathAdapter
from zope.traversing.interfaces import ITraversable

from pyramid.interfaces import IView
from pyramid.interfaces import IRequest
from pyramid.interfaces import IViewClassifier

from pyramid.security import ALL_PERMISSIONS

from pyramid.traversal import find_interface
from pyramid.threadlocal import get_current_request

from nti.appserver import httpexceptions as hexc

from nti.appserver.context_providers import get_joinable_contexts

from nti.appserver import interfaces

from nti.appserver.pyramid_authorization import is_readable

from nti.appserver.workspaces.interfaces import IContainerCollection

from Acquisition import aq_base
from Acquisition.interfaces import IAcquirer

from nti.common.iterables import is_nonstr_iter

from nti.dataserver import authorization_acl as nacl

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import INamedContainer
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import InappropriateSiteError
from nti.dataserver.interfaces import IHomogeneousTypeContainer
from nti.dataserver.interfaces import ISimpleEnclosureContainer
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids import ntiids

from nti.property.property import alias

ITEMS = StandardExternalFields.ITEMS

def root_resource_factory(request):
	"""
	Return an object representing the root folder.

	:return: An :class:`IRootFolder"
	"""
	dataserver = component.getUtility(IDataserver)
	try:
		root = dataserver.root_folder
		return root
	except InappropriateSiteError:
		# If an exception occurs and we have the debug toolbar
		# installed, it makes a new subrequest without using
		# our tweens, so our site isn't setup. If we raise
		# here, we obscure the original exception
		if request.path.startswith('/_debug_toolbar/'):
			return {}
		raise

def dataserver2_root_resource_factory(request):
	"""
	Returns the object that represents the ``/dataserver2``
	portion of the url.
	Used when that part of the URL has been pre-traversed.

	:return: An :class:`IDataserverFolder`
	"""

	dataserver = component.getUtility(IDataserver)
	return dataserver.dataserver_folder

def users_root_resource_factory(request):
	"""
	Returns the object that represents the ``/dataserver2/users``
	portion of the URL.
	"""
	dataserver = component.getUtility(IDataserver)
	return dataserver.users_folder

@interface.implementer(ITraversable, ILocation)
class _AbstractContainerResource(object):

	__acl__ = ()

	def __init__(self, context, request=None, name=None, parent=None):
		"""
		:param context: A container belonging to a user.
		"""
		self.context = context
		self.request = request
		self.__name__ = name or getattr(context, '__name__', None)
		self.__parent__ = parent or getattr(context, '__parent__', None)
		self.__acl__ = nacl.ACL(context)

	resource = alias('context')  # bwc, see, e.g., GenericGetView
	ntiid = alias('__name__')

	@property
	def user(self):
		return find_interface(self, IUser)

@interface.implementer(interfaces.IContainerResource)
class  _ContainerResource(_AbstractContainerResource):

	def traverse(self, key, remaining_path):
		contained_object = self.user.getContainedObject(self.__name__, key)
		if contained_object is None:
			# LocationError is a subclass of KeyError, and compatible
			# with the traverse() interface
			raise LocationError(key)
		# TODO: We might need to chop off an intid portion of the key
		# if it's in new style, forced on it by nti.externalization.externalization.
		# Fortunately, I think everything uses direct OID links and not traversal,
		# or is in a new enough database that the situation doesn't arise.

		return contained_object

class _AbstractPageContainerResource(_AbstractContainerResource):
	"""
	The Pages container's are generally not meant to be traversable
	into the objects of the container, but we do want to allow
	the use of named path adapters.

	To further simplify migration, if we are attempting to traverse
	to a named view of ourself, we traverse to ourself, so long as
	there is a further path. This lets us use named views
	both on this object (Pages(Root)/RecursiveUGD) and named views
	that are subviews without an intermediate traversable object
	(Pages(Root)/RecursiveUGD/feed.atom). Note that this is a hacky
	shortcut.
	"""

	def traverse(self, key, remaining_path):
		try:
			return adapter_request(self, self.request).traverse(key, remaining_path)
		except KeyError:

			# Is there a named view matching the key? If so we want to
			# "traverse" to ourself, so long as we plan to keep going
			if not remaining_path:
				raise

			if component.getSiteManager().adapters.lookup(
					(IViewClassifier, self.request.request_iface, interface.providedBy(self)),
					IView,
					name=key) is None:
				raise

			return self

@interface.implementer(interfaces.INewPageContainerResource)
class _NewPageContainerResource(_AbstractPageContainerResource):
	"""
	A leaf on the traversal tree, existing only to be a named
	thing that we can match views with for data that does
	not yet exist.
	"""

@interface.implementer(interfaces.IPageContainerResource)
class _PageContainerResource(_AbstractPageContainerResource):
	"""
	A leaf on the traversal tree. Exists to be a named thing that
	we can match view names with. Should be followed by the view name.
	"""

@interface.implementer(interfaces.IRootPageContainerResource)
class _RootPageContainerResource(_AbstractPageContainerResource):
	pass

@interface.implementer(interfaces.IObjectsContainerResource)
class _ObjectsContainerResource(_ContainerResource):

	def __init__(self, context, request=None, name=None, parent=None):
		super(_ObjectsContainerResource, self).__init__(context, request, name=name or 'Objects')

	def traverse(self, key, remaining_path):
		ds = component.getUtility(IDataserver)
		result = self._getitem_with_ds(ds, key)
		if result is None:  # pragma: no cover
			raise LocationError(key)

		#XXX Put back in place because we have objects accessible we don't expect to be
		#Let the forbidden_related_context ref through so we don't have to roll all the clients back
		#if not self.request.url.endswith('/@@forbidden_related_context'):
		#	self._check_permission(result)
		
		# Make these things be acquisition wrapped, just as if we'd traversed
		# all the way to them (only if not already wrapped)
		if 	getattr(result, '__parent__', None) is not None and \
			IAcquirer.providedBy(result) and aq_base(result) is result:
			try:
				result = result.__of__(result.__parent__)
			except TypeError:
				# Thrown for "attempt to wrap extension method using an object that is not an extension class instance."
				# In other words, result.__parent__ is not ExtensionClass.Base.
				pass
		return result

	def to_json_body(self, obj):
		result = to_external_object(to_external_object(obj))
		def _clean(m):
			if isinstance(m, collections.Mapping):
				if 'href' in m and not isinstance(m['href'], six.string_types):
					m.pop('href', None)
				values = m.values()
			elif isinstance(m, set):
				values = list(m)
			elif is_nonstr_iter(m):
				values = m
			else:
				values = ()
			for x in values:
				_clean(x)
		_clean(result)
		return result

	def _check_permission(self, context):
		"""
		For generic object requests, we'd like to handle
		the object-level permissioning ourselves in order
		to provide information on where the user *might* obtain
		permission to view the object in the case of 403s.
		"""
		# FIXME We should probably make the endpoint define
		# permissions. We should catch 403s elsewhere and
		# add context there.
		if queryInteraction() is not None and not is_readable(context):
			results = get_joinable_contexts(context)
			response = hexc.HTTPForbidden()
			if results:
				result = LocatedExternalDict()
				result[ITEMS] = results
				response.json_body = self.to_json_body(result)
			raise response

	def _getitem_with_ds(self, ds, key):
		# The dataserver wants to provide user-based security
		# for access with an OID. We can do better than that, though,
		# with the true ACL security we get from Pyramid's path traversal.
		# FIXME: Some objects (SimplePersistentEnclosure, for example) don't
		# have ACLs (ACLProvider) yet and so this path is not actually doing anything.
		# Those objects are dependent on their container structure being
		# traversed to get a correct ACL, and coming in this way that doesn't happen.
		# NOTE: We do not expect to get a fragment here. Browsers drop fragments in URLs.
		# Fragment handling will have to be completely client side.
		result = ntiids.find_object_with_ntiid(key)
		return result

class _NTIIDsContainerResource(_ObjectsContainerResource):
	"""
	This class exists now mostly for backward compat and for the name. It can
	probably go away.
	"""
	def __init__(self, context, request):
		super(_NTIIDsContainerResource, self).__init__(context, request, name='NTIIDs')

class _PseudoTraversableMixin(object):
	"""
	Extend this to support traversing into the Objects and NTIIDs namespaces.
	"""

	# Special virtual keys beneath this object's context. The value
	# is either a factory function or an interface. If an interface,
	# it names a global utility we look up. If a factory function,
	# it takes two arguments, the context and current request (allowing
	# it to be an adapter from those two things, such as an unnamed
	# IPathAdapter).
	_pseudo_classes_ = { 'Objects': _ObjectsContainerResource,
						 'NTIIDs': _NTIIDsContainerResource }

	def _pseudo_traverse(self, key, remaining_path):
		if key in self._pseudo_classes_:
			value = self._pseudo_classes_[key]
			if interface.interfaces.IInterface.providedBy(value):
				# TODO: In some cases, we'll need to proxy this to add the name?
				# And/Or ACL?s
				resource = component.getUtility(value)
			else:
				resource = self._pseudo_classes_[key](self.context, self.request)

			return resource

		raise LocationError(key)

@interface.implementer(ITraversable)
@component.adapter(IDataserverFolder, IRequest)
class Dataserver2RootTraversable(_PseudoTraversableMixin):
	"""
	A traversable for the root folder in the dataserver, providing
	access to a few of the specialized sub-folders, but not all of
	them, and providing access to the other special implied resources
	(Objects and NTIIDs).

	If none of those things work, we look for an :class:`.IPathAdapter` to
	the request and context having the given name.
	"""

	# TODO: The implied resources could (should) actually be persistent. That way
	# they fit nicely and automatically in the resource tree.

	def __init__(self, context, request=None):
		self.context = context
		self.request = request or get_current_request()

	allowed_keys = ('users',)

	def traverse(self, key, remaining_path):
		if key in self.allowed_keys:
			return self.context[key]  # Better be there. Otherwise, KeyError, which fails traversal

		try:
			return self._pseudo_traverse(key, remaining_path)
		except KeyError:
			return adapter_request(self.context, self.request).traverse(key, remaining_path)

@component.adapter(IUser, IRequest)
class _AbstractUserPseudoContainerResource(object):
	"""
	Base class for things that represent pseudo-containers under a user.
	Exists to provide the ACL for such collections.
	"""

	def __init__(self, context, request):
		self.context = context
		self.request = request
		self.__acl__ = nacl.acl_from_aces(nacl.ace_allowing(context, ALL_PERMISSIONS, self),
										  nacl.ace_denying_all(self))
	__parent__ = alias('context')
	user = alias('context')
	resource = alias('context')  # BWC. See GenericGetView

@interface.implementer(ITraversable, interfaces.IPagesResource)
class _PagesResource(_AbstractUserPseudoContainerResource):
	"""
	When requesting /Pages or /Pages(ID), we go through this resource.
	In the first case, we wind up using the user as the resource,
	which adapts to a ICollection and lists the NTIIDs.
	In the latter case, we return a _PageContainerResource.
	"""

	def traverse(self, key, remaining_path):
		resource = None
		if key == ntiids.ROOT:
			# The root is always available
			resource = _RootPageContainerResource(self, self.request, name=key, parent=self.user)
		# What about an owned container, or a shared container? The
		# shared containers take into account our dynamic
		# relationships...however, this is badly split between here
		# and the view classes with each side implementing something
		# of the logic, so that needs to be cleaned up (for example, this side
		# doesn't handle 'MeOnly'; should it? And we wind up building the shared
		# container twice, once here, once in the view)
		elif self.user.getContainer(key) is not None or \
			 self.user.getSharedContainer(key, defaultValue=None) is not None:
			resource = _PageContainerResource(self, self.request, name=key, parent=self.user)
			# Note that the container itself doesn't matter
			# much, the _PageContainerResource only supports a few child items
		else:
			# This page does not exist. But do we have a specific view or path adapter
			# registered for a pseudo-container at that location? If so, let it have it
			# (e.g., Relevant/RecursiveUGD for grandparents)
			# In general, it is VERY WRONG to lie about the existence of a
			# container here by faking of a PageContainerResource. We WANT to return
			# a 404 response in that circumstance, as it is generally
			# not cacheable and more data may arrive in the future.
			if not remaining_path:
				raise LocationError(key)

			resource = _NewPageContainerResource(None, self.request)
			resource.__name__ = key
			resource.__parent__ = self.context

			if (component.queryMultiAdapter((resource, self.request),
											 IPathAdapter,
											 name=remaining_path[0]) is None
				and component.getSiteManager().adapters.lookup(
					(IViewClassifier, self.request.request_iface, interface.providedBy(resource)),
					IView,
					name=remaining_path[0]) is None):
				raise LocationError(key)

			# OK, assume a new container. Sigh.

		# These have the same ACL as the user itself (for now)
		resource.__acl__ = nacl.ACL(self.user)
		return resource

from nti.dataserver.contenttypes.forums.board import DFLBoard
from nti.dataserver.contenttypes.forums.forum import PersonalBlog
from nti.dataserver.contenttypes.forums.board import CommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

def _BlogResource(context, request):
	return IPersonalBlog(context, None)  # Does the user have access to a default forum/blog? If no, 403.

def _CommunityBoardResource(context, request):
	return ICommunityBoard(context, None)

def _DFLBoardResource(context, request):
	return IDFLBoard(context, None)

def _get_named_container_resource(name, context, request):
	collection = component.queryAdapter(context, IContainerCollection, name=name)
	if collection is not None:
		return _ContainerResource(collection, request)

def _DynamicMembershipsResource(context, request):
	return _get_named_container_resource('DynamicMemberships', context, request)

def _DynamicFriendsListResource(context, request):
	return _get_named_container_resource('Groups', context, request)

def _CommunitiesResource(context, request):
	return _get_named_container_resource('Communities', context, request)

def _AllCommunitiesResource(context, request):
	return _get_named_container_resource('AllCommunities', context, request)

@interface.implementer(ITraversable)
@component.adapter(IUser, IRequest)
class UserTraversable(_PseudoTraversableMixin):

	_pseudo_classes_ = {'Pages': _PagesResource,
						 PersonalBlog.__default_name__: _BlogResource,
						 'DynamicMemberships': _DynamicMembershipsResource,
						 'Groups': _DynamicFriendsListResource,
						 'Communities': _CommunitiesResource,
						 'AllCommunities': _AllCommunitiesResource }
	_pseudo_classes_.update(_PseudoTraversableMixin._pseudo_classes_)

	_DENY_ALL = True

	def __init__(self, context, request=None):
		self.context = context
		self.request = request

	def traverse(self, key, remaining_path):
		# First, some pseudo things the user
		# doesn't actually have.
		# We also account for the odata-style traversal here too,
		# by splitting out the key into two parts and traversing.
		# This simplifies the route matching.
		for pfx in 'Pages(', 'Objects(', 'NTIIDs(':
			if key.startswith(pfx) and  key.endswith(')'):
				remaining_path.insert(0, key[len(pfx):-1])
				key = pfx[:-1]

		try:
			return self._pseudo_traverse(key, remaining_path)
		except LocationError:
			pass

		# Is there a named path adapter?
		try:
			return adapter_request(self.context, self.request).traverse(key, remaining_path)
		except LocationError:
			pass

		# Is this an item in the user's workspace?
		# TODO: Implement workspace traversal. That and named path
		# adapters should obviate the need to look into
		# containers

		# Is this a specific, special container ( not the generic UGD
		# containers)? IContainerResource has views registered on it
		# for POST and GET, but the GET is generic, NOT the UGD GET;
		# that's registered for IPageContainer. This should be replaced
		# with one of the above methods.
		cont = self.context.getContainer(key)
		if not (INamedContainer.providedBy(cont)
				or IHomogeneousTypeContainer.providedBy(cont)):
			# It may or may not exist, but you cannot access it at this URL
			raise LocationError(key)

		resource = _ContainerResource(cont, self.request)
		# Allow the owner full permissions. These are the special
		# containers, and no one else can have them.
		resource.__acl__ = nacl.acl_from_aces(nacl.ace_allowing(self.context, ALL_PERMISSIONS, self))
		if self._DENY_ALL:
			resource.__acl__ = resource.__acl__ + nacl.ace_denying_all(self)

		return resource

@interface.implementer(ITraversable)
@component.adapter(ICommunity, IRequest)
class CommunityTraversable(_PseudoTraversableMixin):

	_pseudo_classes_ = { CommunityBoard.__default_name__: _CommunityBoardResource }

	_DENY_ALL = True

	def __init__(self, context, request=None):
		self.context = context
		self.request = request

	def traverse(self, key, remaining_path):
		try:
			return self._pseudo_traverse(key, remaining_path)
		except KeyError:
			# Is there a named path adapter?
			return adapter_request(self.context, self.request).traverse(key, remaining_path)

@interface.implementer(ITraversable)
@component.adapter(IDynamicSharingTargetFriendsList, IRequest)
class DFLTraversable(_PseudoTraversableMixin):

	_pseudo_classes_ = { DFLBoard.__default_name__: _DFLBoardResource }

	_DENY_ALL = True

	def __init__(self, context, request=None):
		self.context = context
		self.request = request

	def traverse(self, key, remaining_path):
		try:
			return self._pseudo_traverse(key, remaining_path)
		except KeyError:
			# Is there a named path adapter?
			return adapter_request(self.context, self.request).traverse(key, remaining_path)

from nti.traversal.traversal import adapter_request  # BWC export

class _resource_adapter_request(adapter_request):
	"""
	Unwraps some of the things done in dataserver_pyramid_views
	when we need to work directly with the model objects.
	"""

	def __init__(self, context, request=None):
		super(_resource_adapter_request, self).__init__(context.resource, request=request)

# Attachments/Enclosures

@interface.implementer(IPathAdapter,
					   ITraversable,
					   IZContained)
@component.adapter(ISimpleEnclosureContainer)
class EnclosureTraversable(object):
	"""
	Intended to be registered as an object in the adapter namespace to
	provide access to attachments. (We implement :class:`zope.traversing.interfaces.IPathAdapter`
	to work with the default ``++adapter`` handler, :class:`zope.traversing.namespaces.adapter`,
	and then we further implement :class:`zope.traversing.interfaces.ITraversable` so we
	can find further resources.)
	"""
	__parent__ = None
	__name__ = 'enclosures'

	def __init__(self, context, request=None):
		self.context = context
		self.__parent__ = context
		self.request = request

	def traverse(self, name, further_path):
		try:
			return self.context.get_enclosure(name)
		except KeyError:
			raise LocationError(self.context, name)

# The Zope resource namespace

from zope.publisher.interfaces.browser import IBrowserRequest, IDefaultBrowserLayer

from zope.traversing.namespace import resource as _zresource

class resource(_zresource):
	"""
	Handles resource lookup in a way compatible with :mod:`zope.browserresource`.
	This package registers resources as named adapters from :class:`.IDefaultBrowserLayer`
	to Interface. We connect the two by making the pyramid request implement
	the right thing.
	"""

	def __init__(self, context, request):
		request = IBrowserRequest(request)
		if not IDefaultBrowserLayer.providedBy(request):
			interface.alsoProvides(request, IDefaultBrowserLayer)  # We lie
		super(resource, self).__init__(context, request)
