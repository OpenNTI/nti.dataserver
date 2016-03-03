#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from zope import interface
from zope import component
from zope.location import location
from zope.location import interfaces as loc_interfaces

from zope.schema import vocabulary

from pyramid.threadlocal import get_current_request

from nti.app.renderers import rest

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces

# make sure we use nti.dataserver.traversal to find the root site
from nti.dataserver.traversal import find_nearest_site as ds_find_nearest_site

from nti.externalization.singleton import SingletonDecorator

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.externalization import to_standard_external_dictionary
from nti.externalization.externalization import toExternalObject, isSyntheticKey

from nti.links import links

from nti.mimetype import mimetype

from nti.traversal import traversal as nti_traversal

from ..interfaces import IContentUnitInfo
from ..interfaces import IUserCapabilityFilter

from ..pyramid_authorization import is_writable

from ..capabilities.interfaces import VOCAB_NAME as CAPABILITY_VOCAB_NAME

from .interfaces import IService
from .interfaces import IWorkspace
from .interfaces import ICollection
from .interfaces import IUserService
from .interfaces import IContainerCollection

@interface.implementer(IExternalObject)
@component.adapter(ICollection)
class CollectionSummaryExternalizer(object):

	def __init__( self, collection ):
		self._collection = collection

	def toExternalObject( self, **kwargs ):
		collection = self._collection
		ext_collection = LocatedExternalDict()
		ext_collection.__name__ = collection.__name__
		ext_collection.__parent__ = collection.__parent__
		ext_collection[StandardExternalFields.CLASS] = 'Collection'
		ext_collection['Title'] = collection.name
		ext_collection['href'] = nti_traversal.normal_resource_path( collection )
		accepts = collection.accepts
		if accepts is not None:
			ext_collection['accepts'] = [mimetype.nti_mimetype_from_object( x ) for x in accepts]
			if nti_interfaces.ISimpleEnclosureContainer.providedBy( collection ):
				ext_collection['accepts'].extend( ('image/*',) )
				ext_collection['accepts'].extend( ('application/pdf',) )
			ext_collection['accepts'].sort() # For the convenience of tests

		_links = datastructures.find_links( self._collection )
		if _links:
			ext_collection[StandardExternalFields.LINKS] = _magic_link_externalizer( _links )

		return ext_collection

@interface.implementer(IExternalObject)
@component.adapter(IContainerCollection)
class ContainerCollectionDetailExternalizer(object):

	def __init__(self, collection ):
		self._collection = collection

	def toExternalObject( self, **kwargs ):
		collection = self._collection
		container = collection.container
		# Feeds can include collections, as a signal of places that
		# can be posted to in order to add items to the feed.
		# Since these things are useful to have at the top level, we do
		# that as well
		kwargs.pop('name', None)
		summary_collection = toExternalObject( collection, name='summary', **kwargs )
		# Copy the basic attributes
		ext_collection = to_standard_external_dictionary( collection, **kwargs )
		# Then add the summary info as top-level...
		ext_collection.update( summary_collection )
		# ... and nested
		ext_collection['Collection'] = summary_collection
		ext_collection[StandardExternalFields.LAST_MODIFIED] = container.lastModified
		# Feeds contain 'entries' which can be internal (inline)
		# or external. Right now we're always inlining.
		# We use our old 'items' convention. It could be either
		# a dictionary or an array

		# TODO: Think about this. We should probably
		# introduce an 'Entry' wrapper for each item so we can add
		# properties to it and not pollute the namespace of each item.
		# This might also facilitate a level of indirection, allowing
		# external out-of-line entries a bit easier.
		# The downside is backward compatibility.
		# TODO: We need to be putting mimetype info on each of these
		# if not already present. Who should be responsible for that?
		def fixup( v_, item ):
			# FIXME: This is similar to the renderer. See comments in the renderer.
			if StandardExternalFields.LINKS in item:
				item[StandardExternalFields.LINKS] = [rest.render_link(link) if nti_interfaces.ILink.providedBy( link ) else link
													  for link
													  in item[StandardExternalFields.LINKS]]
			# TODO: The externalization process and/or the renderer should be handling
			# this entirely. But right now we're the only place with all the relevant info,
			# so we're doing it. But that violates some layers and make us depend on a request.

			# FIXME: These inner nested objects aren't going through the process of getting ACLs
			# applied to them or their lineage. We really want them to be returning ACLLocationProxy
			# objects. Because they have no ACL, then our editing information is incorrect.
			# We have made a first pass at this below with acl_wrapped which is nearly correct
			request = get_current_request()

			if request and is_writable( v_, request ):
				item.setdefault( StandardExternalFields.LINKS, [] )
				if not any( [l['rel'] == 'edit' for l in item[StandardExternalFields.LINKS]]):
					valid_traversal_path = nti_traversal.normal_resource_path( v_ )
					if valid_traversal_path and not valid_traversal_path.startswith( '/' ):
						valid_traversal_path = None
					if valid_traversal_path:
						item[StandardExternalFields.LINKS].append( links.Link( valid_traversal_path,
																			   rel='edit' ) )
			if 'href' not in item and getattr( v_, '__parent__', None ) is not None:
				# Let this thing try to produce its
				# own href
				# TODO: This if test is probably not needed anymore, with zope.location.traversing
				# it will either work or raise
				try:
					valid_traversal_path = nti_traversal.normal_resource_path( v_ )
					if valid_traversal_path and valid_traversal_path.startswith( '/' ):
						item['href'] = valid_traversal_path
				except TypeError:
					# Usually "Not enough context information to get all parents"
					pass
			return item

		if 	isinstance( container, collections.Mapping ) and \
			not getattr(container, '_v_container_ext_as_list', False):
			ext_collection['Items'] = { k: fixup(v,toExternalObject(v,**kwargs)) for k,v in container.iteritems()
										if not isSyntheticKey( k )}
		else:
			ext_collection['Items'] = [fixup(v,toExternalObject(v, **kwargs)) for v in container]

		# Need to add hrefs to each item.
		# In the near future, this will be taken care of automatically.
		temp_res = location.Location()
		temp_res.__parent__ = collection
		for item in (ext_collection['Items'].itervalues()
					 if isinstance(ext_collection['Items'], collections.Mapping)
					 else ext_collection['Items']):
			if 'href' not in item and 'ID' in item:
				temp_res.__name__ = item['ID']
				item['href'] = nti_traversal.normal_resource_path( temp_res )

		return ext_collection

def _magic_link_externalizer(_links):
	# Note that we are handling link traversal for
	# links that are string based here. Somewhere up the line
	# we're losing context and failing to render if we don't.
	# We only do this for things that are set up specially in
	# this module.
	for l in _links:
		if l.target == getattr(l, '__name__', None):
			# We know the ntiid gets used as the href
			l.ntiid = nti_traversal.normal_resource_path(l)
			l.target = l
	return _links

@interface.implementer(IExternalObject)
@component.adapter(IWorkspace)
class WorkspaceExternalizer(object):

	def __init__( self, workspace ):
		self._workspace = workspace

	def toExternalObject( self, **kwargs ):
		kwargs.pop('name', None)
		result = LocatedExternalDict()
		result[StandardExternalFields.CLASS] = 'Workspace'
		result['Title'] = self._workspace.name or getattr( self._workspace, '__name__', None )
		items = [toExternalObject( collection, name='summary', **kwargs )
				 for collection
				 in self._workspace.collections]
		result['Items'] = items
		_links = datastructures.find_links( self._workspace )
		if _links:
			result[StandardExternalFields.LINKS] = _magic_link_externalizer( _links )
		return result

def _create_search_links( parent ):
	# Note that we are providing a complete link with a target
	# that is a string and also the name of the link. This is
	# a bit wonky and cooperates with how the CollectionSummaryExternalizer
	# wants to deal with links
	# TODO: Hardcoding both things
	search_parent = location.Location()
	search_parent.__name__ = 'Search'
	search_parent.__parent__ = parent
	ugd_link = links.Link( 'RecursiveUserGeneratedData', rel='UGDSearch' )
	unified_link = links.Link( 'UnifiedSearch', rel='UnifiedSearch' )
	result = (ugd_link, unified_link)
	for lnk in result:
		lnk.__parent__ = search_parent
		lnk.__name__ = lnk.target
		interface.alsoProvides( lnk, loc_interfaces.ILocation )
	return result

@interface.implementer(IExternalObject)
@component.adapter(IContentUnitInfo)
class _NTIIDEntryExternalizer(object):

	def __init__( self, context ):
		self.context = context

	def toExternalObject(self, **kwargs):
		result = to_standard_external_dictionary( self.context, **kwargs )
		return result

from nti.links.externalization import render_link

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IContentUnitInfo) # TODO: IModeledContent?
class ContentUnitInfoHrefDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		if 'href' in mapping:
			return

		try:
			# Some objects are not in the traversal tree. Specifically,
			# chatserver.IMeeting (which is IModeledContent and IPersistent)
			# Our options are to either catch that here, or introduce an
			# opt-in interface that everything that wants 'edit' implements
			nearest_site = ds_find_nearest_site( context )
		except TypeError:
			nearest_site = None

		if nearest_site is None:
			logger.debug("Not providing href links for %s, could not find site",
						 type(context) )
			return

		link = links.Link( nearest_site, elements=('Objects', context.ntiid) )
		link.__parent__ = getattr(nearest_site, '__parent__', None) # Nearest site may be IRoot, which has no __parent__
		link.__name__ = ''
		interface.alsoProvides( link, loc_interfaces.ILocation )

		mapping['href'] = render_link( link, nearest_site=nearest_site )['href']

@interface.implementer(IExternalObject)
@component.adapter(IService)
class ServiceExternalizer(object):

	def __init__( self, service ):
		self.context = service

	def toExternalObject( self, **kwargs ):
		result = LocatedExternalDict()
		result.__parent__ = self.context.__parent__
		result.__name__ = self.context.__name__
		result[StandardExternalFields.CLASS] = 'Service'
		result[StandardExternalFields.MIMETYPE] = mimetype.nti_mimetype_with_class( 'Service' )
		result['Items'] = [toExternalObject(ws, **kwargs) for ws in self.context.workspaces]
		return result

@component.adapter(IUserService)
class UserServiceExternalizer(ServiceExternalizer):
	"""
	Expose our capabilities and site-level community.
	"""

	def toExternalObject(self, **kwargs):
		result = super(UserServiceExternalizer,self).toExternalObject(**kwargs)

		# TODO: This is almost hardcoded. Needs replaced with something dynamic.
		# Querying the utilities for the user, which would be registered for specific
		# IUser types or something...
		registry = vocabulary.getVocabularyRegistry()
		cap_vocab = registry.get(self.context.user, CAPABILITY_VOCAB_NAME)
		capabilities = {term.value for term in cap_vocab}

		# Now filter out capabilities.
		from IPython.core.debugger import Tracer;Tracer()()
		for cap_filter in component.subscribers((self.context.user,),
												IUserCapabilityFilter):
			capabilities = cap_filter.filterCapabilities( capabilities )

		result['CapabilityList'] = list( capabilities )

		# Now our community name
		site_policy = component.queryUtility( ISitePolicyUserEventListener )
		community_username = getattr(site_policy, 'COM_USERNAME', '')
		if community_username:
			result['SiteCommunity'] = community_username
		return result
