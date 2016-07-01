#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.location.interfaces import ILocation

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.common.property import Lazy

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfolder.interfaces import IRootFolder, ILockedFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_UPDATE
from nti.dataserver.authorization import ACT_DELETE 

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from nti.links.links import Link

from nti.namedfile.interfaces import INamedFile

LINKS = StandardExternalFields.LINKS

def _create_link(context, rel, name=None, method=None, params=None):
	elements = () if not name else (name,)
	link = Link(context, rel=rel, elements=elements, 
				method=method, params=params)
	interface.alsoProvides(link, ILocation)
	link.__name__ = ''
	link.__parent__ = context
	return link

@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _NamedFolderLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	@Lazy
	def _acl_decoration(self):
		result = getattr(self.request, 'acl_decoration', True)
		return result

	def _predicate(self, context, result):
		return self._acl_decoration and self._is_authenticated

	def _do_decorate_external(self, context, result):
		request = self.request
		_links = result.setdefault(LINKS, [])

		# read based ops
		if has_permission(ACT_READ, context, request):
			_links.append(_create_link(context, "tree", "@@tree",
									   params={'flat':False}))
			_links.append(_create_link(context, "export", "@@export"))
			_links.append(_create_link(context, "contents", "@@contents",
									   params={'depth':0}))
			_links.append(_create_link(context, "search", "@@search"))

		# update based ops
		if has_permission(ACT_UPDATE, context, request):
			_links.append(_create_link(context, "mkdir", "@@mkdir", method='POST'))
			_links.append(_create_link(context, "mkdirs", "@@mkdirs", method='POST'))
			_links.append(_create_link(context, "upload", "@@upload", method='POST'))
			_links.append(_create_link(context, "import", "@@import", method='POST'))

			if not ILockedFolder.providedBy(context):
				_links.append(_create_link(context, "move", "@@move", method='POST'))
				_links.append(_create_link(context, "clear", "@@clear", method='POST'))
				_links.append(_create_link(context, "rename", "@@rename", method='POST'))
						
		if 		has_permission(ACT_DELETE, context, request) \
			and not ILockedFolder.providedBy(context):
			_links.append(_create_link(context, rel="delete", method='DELETE'))

		# non root folders
		if 		not IRootFolder.providedBy(context) \
			and has_permission(ACT_UPDATE, context, request):
			_links.append(_create_link(context, "move", "@@move", method='POST'))
			_links.append(_create_link(context, "rename", "@@rename", method='POST'))

@component.adapter(INamedFile)
@interface.implementer(IExternalObjectDecorator)
class _NamedFileLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	@Lazy
	def _acl_decoration(self):
		result = getattr(self.request, 'acl_decoration', True)
		return result

	def _predicate(self, context, result):
		parent = getattr(context, '__parent__', None)
		return 		parent is not None \
				and self._acl_decoration \
				and self._is_authenticated \
				and INamedContainer.providedBy(parent)

	def _do_decorate_external(self, context, result):
		request = self.request
		_links = result.setdefault(LINKS, [])
		if 		IContentBaseFile.providedBy(context) \
			and has_permission(ACT_READ, context, request):
			_links.append(_create_link(context, rel="external", 
									   name="@@external", method='GET'))
			_links.append(_create_link(context, rel="associations", 
									   name="@@associations", method='GET'))

		if 	has_permission(ACT_DELETE, context, request):
			_links.append(_create_link(context, rel="delete", method='DELETE'))

		if 	has_permission(ACT_UPDATE, context, request):
			_links.append(_create_link(context, rel="copy", name="@@copy", method="POST"))
			_links.append(_create_link(context, rel="move", name="@@move", method="POST"))
			_links.append(_create_link(context, rel="rename", name="@@rename", method='POST'))
			if IContentBaseFile.providedBy(context):
				_links.append(_create_link(context, rel="associate", 
										   name="@@associate", method='POST'))

@component.adapter(INamedFile)
@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _ContextPathDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def compute_path(self, context):
		result = []
		while context is not None and not IRootFolder.providedBy(context):
			try:
				result.append(context.__name__)
				context = context.__parent__
			except AttributeError:
				break
		result.reverse()
		result = '/'.join(result)
		result = '/' + result if not result.startswith('/') else result
		return result
	
	def _do_decorate_external(self, context, result):
		path = result.get('path', None)
		if not path and INamedContainer.providedBy(context.__parent__):
			result['path'] = self.compute_path(context)
