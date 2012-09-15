#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import six
import urllib
import collections

from zope import interface
from zope import component
from zope.location import location
from zope.location import interfaces as loc_interfaces
import zope.traversing.interfaces


from nti.dataserver import traversal
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import StandardExternalFields
from nti.dataserver.mimetype import nti_mimetype_from_object

from nti.ntiids import ntiids

import nti.dataserver.interfaces as nti_interfaces

def _root_for_ntiid_link( link, nearest_site ):
	# Place the NTIID reference under the most specific place possible: the owner,
	# if we can get one, otherwise the global Site
	root = None
	target = link.target
	if nti_interfaces.ICreated.providedBy( target ) and target.creator:
		try:
			root = traversal.normal_resource_path( target.creator )
		except TypeError:
			pass
	if root is None and nti_interfaces.ICreated.providedBy( link ) and link.creator:
		try:
			root = traversal.normal_resource_path( link.creator )
		except TypeError:
			pass

	if root is None:
		root = traversal.normal_resource_path( nearest_site )

	return root

def render_link( link, nearest_site=None ):
	"""
	:param link: The link to render. Optionally, the link may be
		:class:`loc_interfaces.ILocation` if we need to find a site. The target
		of the link can be a string, in which case it should be a complete path or an NTIID,
		or it can be an object with a complete lineage. If the target is an NTIID string, we
		will try to find the creating user of the link (or its target) to provide a more localized
		representation; the link or its target has to implement :class:`nti_interfaces.ICreated`
		for this to work or we will use the nearest site (probably the root).
	:type link: :class:`nti_interfaces.ILink`
	"""


	target = link.target
	rel = link.rel
	content_type = link.target_mime_type or nti_mimetype_from_object( target )

	href = None
	ntiid = getattr( target, 'ntiid', None ) \
		or getattr( target, 'NTIID', None ) \
		or (isinstance(target,six.string_types) and ntiids.is_valid_ntiid_string(target) and target)
	if ntiid and not nti_interfaces.IEnclosedContent.providedBy( target ):
		# Although enclosures have an NTIID, we want to avoid using it
		# if possible because it has a much nicer pretty url.
		href = ntiid
		# We're using ntiid as a backdoor for arbitrary strings.
		# But if it really is an NTIID, then direct it specially if
		# we can.
		# FIXME: Hardcoded paths.
		# TODO: Somewhere in the site there should be an object that represents each of these,
		# and we should be able to find it, get a traversal path for it, and use it here.
		# That object should implement the lookup behaviour found currently in ntiids.
		if ntiids.is_valid_ntiid_string( ntiid ):
			if nearest_site is None:
				nearest_site = traversal.find_nearest_site( link )

			root = _root_for_ntiid_link( link, nearest_site )

			if ntiids.is_ntiid_of_type( ntiid, ntiids.TYPE_OID ):
				href = root + '/Objects/' + urllib.quote( ntiid )
			else:
				href = root + '/NTIIDs/' + urllib.quote( ntiid )

	elif traversal.is_valid_resource_path( target ):
		href = target
	else:
		# This will raise a LocationError if something is broken
		# in the chain. That shouldn't happen and needs to be dealt with
		# at dev time.
		__traceback_info__ = rel, link.elements # next fun puts target in __traceback_info__
		href = traversal.normal_resource_path( target )


	assert href

	# Join any additional path segments that were requested
	if link.elements:
		href = href + '/' + '/'.join( link.elements )
		# TODO: quoting
	result = component.getMultiAdapter( (), ext_interfaces.ILocatedExternalMapping )
	result.update( { StandardExternalFields.CLASS: 'Link',
					 StandardExternalFields.HREF: href,
					 'rel': rel } )
	if content_type:
		result['type'] = content_type
	if ntiids.is_valid_ntiid_string( ntiid ):
		result['ntiid'] = ntiid
	if not traversal.is_valid_resource_path( href ) and not ntiids.is_valid_ntiid_string( href ): # pragma: no cover
		# This shouldn't be possible anymore.
		__traceback_info__ = href, link, target, nearest_site
		raise zope.traversing.interfaces.TraversalError(href)

	if ILinkExternalHrefOnly_providedBy( link ):
		# The marker that identifies the link should be replaced by just the href
		# Because of the decorator, it's easiest to just do this here
		result = result['href']

	return result


@interface.implementer(ext_interfaces.IInternalObjectExternalizer)
@component.adapter(nti_interfaces.ILink)
class LinkExternal(object):
	"See :func:`render_link`"

	def __init__( self, context ):
		self.context = context

	def toExternalObject(self):
		return render_link( self.context )

ILink_providedBy = nti_interfaces.ILink.providedBy
ILinkExternalHrefOnly_providedBy = nti_interfaces.ILinkExternalHrefOnly.providedBy
_MutableSequence = collections.MutableSequence
_MutableMapping = collections.MutableMapping
LINKS = StandardExternalFields.LINKS

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(object)
class LinkExternalObjectDecorator(object):
	"""
	An object decorator which (comes after the mapping decorators)
	to clean up any links that are added by decorators that didn't get rendered.
	"""
	def __init__( self, context ):
		pass

	def decorateExternalObject(self, context, obj):
		if isinstance( obj, _MutableSequence ):
			for i, x in enumerate(obj):
				if ILink_providedBy( x ):
					obj[i] = render_link( x )
		elif isinstance( obj, _MutableMapping ) and obj.get( LINKS, () ):
			obj[LINKS] = [render_link(link) if ILink_providedBy(link) else link
						  for link
						  in obj[LINKS]]
