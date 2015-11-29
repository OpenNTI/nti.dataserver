#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A decorator for the 'edit' link

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.location.interfaces import ILocation

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import is_writable
from nti.appserver.pyramid_authorization import is_deletable

from nti.common.property import Lazy

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICreated
from nti.dataserver.interfaces import IShouldHaveTraversablePath

# make sure we use nti.dataserver.traversal to find the root site
from nti.dataserver.traversal import find_nearest_site as ds_find_nearest_site

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link
from nti.links.externalization import render_link

LINKS = StandardExternalFields.LINKS
IShouldHaveTraversablePath_providedBy = IShouldHaveTraversablePath.providedBy

@interface.implementer(IExternalMappingDecorator)
class EditLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):
	"""
	Adds the ``edit`` link relationship to objects that are persistent
	(because we have to be able to generate a URL and we need the OID).

	Subclasses may override :meth:`_has_permission` if this definition
	needs changed.

	Also, since this is the most convenient place, decorates objects
	with a top-level ``href`` link. This may or may not always be
	correct and performant. Be careful what you register this for.
	"""

	#: Subclasses can set this to false to force the use of
	#: object identifies
	allow_traversable_paths = True

	#: The method to use to send to the link
	link_method = None

	def _make_link_to_context(self, context):
		if self.allow_traversable_paths and IShouldHaveTraversablePath_providedBy(context):
			link = Link(context,
						rel='edit',
						method=self.link_method)
			link.__parent__ = context.__parent__
			link.__name__ = context.__name__
		else:
			link = Link(to_external_ntiid_oid(context),
						rel='edit',
						method=self.link_method)
			link.__parent__ = context
			# XXX: Is this necessary anymore?
			link.__name__ = ''
			interface.alsoProvides(link, ILocation)

		try:
			# We make the link ICreated so that we go to the /Objects/
			# path under the user to access it, if we are writing
			# out OID links. The only reason I (JAM) can think this matters,
			# at this writing, is for legacy tests.
			# Since community objects have never been traversable to /Objects/
			# (Actually, nothing besides IUser is), and we don't necessarily
			# want to make them so, don't do it in that case
			creator = context.creator
			if IUser.providedBy(creator):
				link.creator = context.creator
				interface.alsoProvides(link, ICreated)
		except AttributeError:
			pass
		return link

	@Lazy
	def _acl_decoration(self):
		result = getattr(self.request, '_acl_decoration', True)
		return result

	def _preflight_context(self, context):
		"""
		We must either have a persistent object.
		XXX: We used to allow edits on non-persistent objects with traversable
		paths.
		"""
		return getattr(context, '_p_jar', None)

	def _has_permission(self, context):
		return is_writable(context, request=self.request)

	def _predicate(self, context, result):
		return 		self._acl_decoration \
				and AbstractAuthenticatedRequestAwareDecorator._predicate(self, context, result) \
				and self._preflight_context(context)

	def _do_decorate_external(self, context, mapping):
		# make sure there is no edit link already
		# permission check is relatively expensive

		links = mapping.setdefault(LINKS, [])
		needs_edit = True
		for l in links:
			if getattr(l, 'rel', None) == 'edit':
				needs_edit = False
				break

		needs_edit = needs_edit and self._has_permission(context)
		needs_href = 'href' not in mapping

		if not (needs_edit or needs_href):
			return

		# TODO: This is weird, assuming knowledge about the URL structure here
		# Should probably use request ILocationInfo to traverse back up to the ISite
		__traceback_info__ = context, mapping
		try:
			# Some objects are not in the traversal tree. Specifically,
			# chatserver.IMeeting (which is IModeledContent and IPersistent)
			# Our options are to either catch that here, or introduce an
			# opt-in interface that everything that wants 'edit' implements
			nearest_site = ds_find_nearest_site(context)
		except TypeError:
			nearest_site = None

		if nearest_site is None:
			logger.debug("Not providing edit/href links for %s, could not find site",
						  getattr(context, '__class__', type(context)))
			return

		try:
			edit_link = self._make_link_to_context(context)
		except TypeError:  # commonly a failure to adapt something
			logger.debug("Not providing edit/href links for %s, failed to get link",
						  getattr(context, '__class__', type(context)),
						  exc_info=True)
			return

		if needs_edit:
			links.append(edit_link)
		if needs_href or needs_edit:
			# For cases that we can, make edit and the toplevel href be the same.
			# this improves caching
			mapping['href'] = render_link(edit_link, nearest_site=nearest_site)['href']

			# We used to catch this when rendering a link:
			# except (KeyError,ValueError,AssertionError,TypeError):
			# 	logger.log( loglevels.TRACE, "Failed to get href link for %s", context, exc_info=True )
			# But that could still fail later when the edit link is rendered?
			# So why catch here? Does rendering the edit link also catch?

			# NOTE: This may be a minor perf degredaion? Think through the implications of this
			# FIXME: temporary place to ensure that everything is always given
			# a unique, top-level 'href'. The one-and-only client is currently depending upon this.
			# FIXME: Note duplication of IShouldHaveTraversablePath checks; cf pyramid_renderers

class OIDEditLinkDecorator(EditLinkDecorator):
	"""
	A decorator for persistent objects, producing stable OIDs.
	"""

	allow_traversable_paths = False

class OIDEditOrDeleteLinkDecorator(OIDEditLinkDecorator):
	"""
	If not writable, how about delete?
	"""

	def _has_permission(self, context):
		writable = super(OIDEditOrDeleteLinkDecorator, self)._has_permission(context)
		if writable:
			return writable
		deleteable = is_deletable(context, request=self.request)
		if deleteable:
			self.link_method = 'DELETE'
			return deleteable

class UserEditLinkDecorator(EditLinkDecorator):
	"""
	A custom decorator for users.

	The general ACL for users is expensive to compute,
	if the database cache is cold. Through our special knowledge
	of the ACL for a user, we can skip that and only return
	the link to the user himself.

	See all :class:`nti.dataserver.authorization_acl._UserACLProvider`
	"""

	def _has_permission(self, context):
		return self.remoteUser == context
