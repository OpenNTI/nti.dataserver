#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of cache controllers, both generic and concrete.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from hashlib import md5

from zope import component
from zope import interface

from zope.file import interfaces as zf_interfaces

import pyramid.httpexceptions

from pyramid.threadlocal import get_current_request

from nti.app.renderers.interfaces import IExternalCollection
from nti.app.renderers.interfaces import IUnModifiedInResponse
from nti.app.renderers.interfaces import IUncacheableInResponse
from nti.app.renderers.interfaces import IResponseCacheController
from nti.app.renderers.interfaces import IPrivateUncacheableInResponse
from nti.app.renderers.interfaces import IUserActivityExternalCollection
from nti.app.renderers.interfaces import IETagCachedUGDExternalCollection
from nti.app.renderers.interfaces import IPreRenderResponseCacheController
from nti.app.renderers.interfaces import ILongerCachedUGDExternalCollection

from nti.appserver import traversal
from nti.appserver import interfaces as app_interfaces

from nti.dataserver import flagging
from nti.dataserver import interfaces as nti_interfaces

def default_vary_on(request):
	vary_on = []
	# It is important to be consistent with these responses;
	# they should not change if the header is absent from the request
	# since it is an implicit parameter in our decision making

	# our responses vary based on the Accept parameter, since
	# that informs representation
	vary_on.append(b'Accept')
	vary_on.append(b'Accept-Encoding')  # we expect to be gzipped
	vary_on.append(b'Origin')

	# vary_on.append( b'Host' ) # Host is always included
	return vary_on

@interface.provider(IResponseCacheController)
def default_cache_controller(data, system):
	request = system['request']
	response = request.response
	vary_on = default_vary_on(request)

	def _prep_cache(rsp):
		rsp.vary = vary_on
		rsp.cache_control.must_revalidate = True
		# If we have applied an Last Modified date, but we do not give any indication of
		# freshness, then some heuristics come into play that can screw us over.
		# Such a response "allows a cache to assign its own freshness lifetime" and if something
		# is defined as fresh, 'must-revalidate' is meaningless.
		# Moreover, if no freshness is provided, then it is assumed to be fresh
		# "if the cache has seen the representation recently, and it was modified relatively long ago."
		# We set some age guideline here to avoid that trap:
		if rsp.cache_control.max_age is None:
			rsp.cache_control.max_age = 0  # You must opt-in for some non-zero lifetime
			# (Setting it to 0 is equivalent to setting no-cache)

		if request.authenticated_userid is not None:
			rsp.cache_control.private = True

	end_to_end_reload = False  # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9.4
	if request.pragma == 'no-cache' or request.cache_control.no_cache:  # None if not set, '*' if set without names
		end_to_end_reload = True

	# We provide non-semantic ETag support based on the current rendering.
	# This lets us work with user-specific things like edit links and user
	# online status, but it is not the most efficient way to do things.
	# It does let us support 'If-None-Match', but it does not let us support
	# If-Match, unfortunately.

	if not response.etag:
		body = system.get('nti.rendered')
		if body is not None:
			response.md5_etag(body, set_content_md5=True)
	if 	response.etag and request.accept_encoding \
		and 'gzip' in request.accept_encoding \
		and not response.etag.endswith(b'./gz'):
		# The etag is supposed to vary between encodings
		response.etag += b'./gz'

	if not end_to_end_reload and response.status_int == 200:  # We will do caching
		# If they give us both an etag and a last-modified, and the etag doesn't match,
		# we MUST NOT generate a 304. Last-Modified is considered a weak validater,
		# and we could in theory still generate a 304 if etag matched and last-mod didn't.
		# However, we're going for strong semantics.
		votes = []
		if response.etag and request.if_none_match:
			votes.append(response.etag in request.if_none_match)

		# Not Modified must also be true, if given
		if response.last_modified is not None and request.if_modified_since:
			votes.append(response.last_modified <= request.if_modified_since)
			# Since we know a modification date, respect If-Modified-Since. The spec
			# says to only do this on a 200 response
			# This is a pretty poor time to do it, after we've done all this work

		if votes and all(votes):
			not_mod = pyramid.httpexceptions.HTTPNotModified()
			not_mod.last_modified = response.last_modified
			not_mod.cache_control = response.cache_control
			_prep_cache(not_mod)
			if response.etag:
				not_mod.etag = response.etag
			raise not_mod

	response.vary = vary_on
	# We also need these to be revalidated; allow the original response
	# to override, trumped by the original request
	if end_to_end_reload:
		# No, that's not right. That gets us into an endless cycle with the client
		# and us bouncing 'no-cache' back and forth
		# response.cache_control.no_cache = True
		# response.pragma = 'no-cache'
		# so lets try something more subtle
		response.cache_control.max_age = 0
		response.cache_control.proxy_revalidate = True
		response.cache_control.must_revalidate = True
		response.expires = 0

	elif not response.cache_control.no_cache and not response.cache_control.no_store:
		_prep_cache(response)
	return response

@interface.implementer(IResponseCacheController)
def default_cache_controller_factory(d):
	return default_cache_controller

@interface.provider(IResponseCacheController)
def uncacheable_cache_controller(data, system):
	request = system['request']
	response = request.response

	# No-cache should be enough to request that
	# this is not used without revalidation;
	# we explicitly turn on revalidation as well
	response.cache_control.no_cache = True
	response.cache_control.proxy_revalidate = True
	response.cache_control.must_revalidate = True

	# Further, the age
	response.cache_control.max_age = 0
	return response

@interface.implementer(IResponseCacheController)
@component.adapter(IUncacheableInResponse)
def uncacheable_factory(data):
	return uncacheable_cache_controller

@interface.provider(IResponseCacheController)
def private_uncacheable_cache_controller(data, system):
	response = uncacheable_cache_controller(data, system)
	# Our typical reason for doing this is
	# sensitive or authentication related information,
	# so being explicit that it's private serves as
	# additional documentation
	response.cache_control.private = True

	# We already said not to cache, but because it's private
	# also request not even any temporary storage
	response.cache_control.no_store = True

	# Likewise, try to vary on cookie in case we are
	# doing authentication in cookies. (Note: pragmatically
	# this doesn't seem to have any effect so it's also
	# mostly documentation).
	response.vary = list(response.vary or ()) + ['Cookie']

	return response

@interface.implementer(IResponseCacheController)
@component.adapter(IPrivateUncacheableInResponse)
def private_uncacheable_factory(data):
	return private_uncacheable_cache_controller

@interface.provider(IResponseCacheController)
def unmodified_cache_controller(data, system):
	"""
	Use this when the response shouldn't be cached based on last modified dates, and we have
	no valid Last-Modified data to provide the browser (any that
	we think we have so far is invalid for some reason and will be
	discarded).

	This still allows for etag based caching.
	"""
	request = system['request']
	response = request.response
	response.last_modified = None  #
	request.if_modified_since = None
	response = default_cache_controller(data, system)
	response.last_modified = None  # in case it changed

@interface.implementer(IResponseCacheController)
@component.adapter(IUnModifiedInResponse)
def unmodified_factory(data):
	return unmodified_cache_controller

def md5_etag(*args):
	digest = md5()
	for arg in args:
		if arg:
			digest.update(arg.encode('utf-8') if isinstance(arg, unicode) else str(arg))
	return digest.digest().encode('base64').replace('\n', '').strip('=')
_md5_etag = md5_etag

@interface.implementer(IPreRenderResponseCacheController)
def UseTheRequestContextCacheController(context):
	"""
	Instead of using the return value from the view, use the context of the request.
	This is useful when the view results are directly derived from the context,
	and the context has more useful information than the result does. It allows
	you to register an adapter for the context, and use that *before* calculating the
	view. If you do have to calculate the view, you are assured that the ETag values
	that the view results create are the same as the ones you checked against.
	"""
	# TODO: We could probably detect that response.etag has been set, and
	# not do this again. The common case is that the object we are going to return
	# here would already have been called on the context before the view executed;
	# we are called after the view. Nothing should have changed on the context object in the
	# meantime.
	return IPreRenderResponseCacheController(get_current_request().context)

@interface.implementer(IPreRenderResponseCacheController)
class AbstractReliableLastModifiedCacheController(object):
	"""
	Things that have reliable last modified dates go here
	for pre-rendering etag support.
	"""

	remote_user = None

	def __init__(self, context, request=None):
		self.context = context
		self.request = request

	max_age = 300

	@property
	def _context_specific(self):
		return ()

	@property
	def _context_lastModified(self):
		return self.context.lastModified

	def __call__(self, context, system):
		request = system['request']
		self.request = request
		self.remote_user = request.authenticated_userid
		response = request.response
		last_modified = self._context_lastModified
		response.last_modified = last_modified
		response.etag = _md5_etag(bytes(last_modified), self.remote_user, *self._context_specific)
		response.cache_control.max_age = self.max_age  # arbitrary
		# Let this raise the not-modified if it will
		return default_cache_controller(context, system)

_AbstractReliableLastModifiedCacheController = AbstractReliableLastModifiedCacheController  # BWC

@component.adapter(zf_interfaces.IFile)
class _ZopeFileCacheController(_AbstractReliableLastModifiedCacheController):
	# All of our current uses of zope file objects replace them with
	# new objects, they don't overwrite. so we can use the _p_oid and _p_serial
	# of the IFile as a proxy for the underlying bits of the blob.

	max_age = 3600  # an hour

	@property
	def _context_lastModified(self):
		try:
			return self.context.lastModified
		except AttributeError:
			last_mod_parent = traversal.find_interface(self.request.context, nti_interfaces.ILastModified)
			if last_mod_parent is not None:
				return last_mod_parent.lastModified

	@property
	def _context_specific(self):
		return self.context._p_oid, self.context._p_serial

@interface.implementer(IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.IEntity)
class _EntityCacheController(_AbstractReliableLastModifiedCacheController):
	"""
	Entities have reliable last modified dates. We use this to
	produce an ETag without rendering. We also adjust the cache
	expiration.
	"""

	@property
	def _context_specific(self):
		return (self.context.username,)

@interface.implementer(IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.IUser)
class _UserCacheController(_EntityCacheController):
	"""
	No op.
	"""
	# In the past, when we added presence info directly
	# to the external rep of a user, we needed to include
	# that in the etag. We no longer do that.

@interface.implementer(IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.IModeledContent)
class _ModeledContentCacheController(_AbstractReliableLastModifiedCacheController):
	"""
	Individual bits of modeled content have reliable last modified dates
	"""

	max_age = 0  # XXX arbitrary

	@property
	def _context_specific(self):
		# We take into account the creator of the object and its local ID.
		# We also take into account the flagging status of the object,
		# since flagging does not change the modification time.
		flagged = False
		if self.remote_user:
			try:
				flagged = flagging.flags_object(self.context, self.remote_user)
			except LookupError:  # Usually ComponentLookupError, in tests
				flagged = None

		try:
			return self.context.creator.username, self.context.__name__, str(flagged)
		except AttributeError:
			return self.context.__name__, str(flagged)

@interface.implementer(IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.ITranscript)
class _TranscriptCacheController(_ModeledContentCacheController):
	"""
	Takes into account the individual flagging status of each message, since
	last modified times are not updated by flagging.
	"""

	@property
	def _context_specific(self):
		flags = ()
		if self.remote_user:
			flags = tuple([flagging.flags_object(m, self.remote_user) for m in self.context.Messages])
		return super(_TranscriptCacheController, self)._context_specific + flags

@interface.implementer(IPreRenderResponseCacheController)
@component.adapter(IExternalCollection)
class _ExternalCollectionCacheController(_AbstractReliableLastModifiedCacheController):
	"""
	Arbitrary collections coming from this specific place have reliable last-modified dates.
	"""

	max_age = 0  # XXX arbitrary

	@property
	def _context_specific(self):
		return self.context.__name__, len(self.context)

@component.adapter(ILongerCachedUGDExternalCollection)
class _LongerCachedUGDExternalCollectionCacheController(_ExternalCollectionCacheController):

	max_age = 120  # XXX arbitrary

@component.adapter(IETagCachedUGDExternalCollection)
class _ETagCachedUGDExternalCollectionCacheController(_ExternalCollectionCacheController):
	# We are guaranteed to get great caching because every time the data changes
	# we change the link we generate. We don't need to take our own
	# modification date into account.

	max_age = 3600

	@property
	def _context_lastModified(self):
		return 0

from nti.app.authentication import get_remote_user

@component.adapter(IUserActivityExternalCollection)
class _UserActivityViewCacheController(_ExternalCollectionCacheController):
	"""
	If the owner asks for his own activity, we allow for less caching.
	If you ask for somebody elses, it may be slightly more stale.
	"""

	max_age = 0

	def __call__(self, context, system):
		request = system['request']
		remote_user = get_remote_user(request)
		if remote_user and remote_user != context.__data_owner__:
			self.max_age = _LongerCachedUGDExternalCollectionCacheController.max_age
		return _ExternalCollectionCacheController.__call__(self, context, system)

@interface.implementer(IPreRenderResponseCacheController)
@component.adapter(app_interfaces.IContentUnitInfo)
class _ContentUnitInfoCacheController(object):
	# rendering this doesn't take long, and we need the rendering
	# process to decorate us with any sharing preferences that may change
	# and update our modification stamp (this is why we can't be a
	# subclass of _AbstractReliableLastModifiedCacheController)

	# We used to set a cache-contral max-age header of five minutes
	# because that sped up navigation in the app noticebly. But it
	# also led to testing problems if the tester switched accounts.
	# The fix is to have the app cache these objects itself,
	# and we go back to ETag/LastModified caching based on
	# the rendered form.
	# See Trell #2962 https://trello.com/c/1TGen4z1

	def __init__(self, context):
		pass

	def __call__(self, context, system):
		return system['request'].response

from zope.proxy.decorator import SpecificationDecoratorBase

@interface.implementer(IUncacheableInResponse)
class _UncacheableInResponseProxy(SpecificationDecoratorBase):
	"""
	A proxy that itself implements UncacheableInResponse. Note that we
	must extend SpecificationDecoratorBase if we're going to be
	implementing things, otherwise if we try to do
	`interface.alsoProvides` on a plain ProxyBase object it falls
	through to the original object, which defeats the point.
	"""

	# when/if these are pickled, they are pickled as their original type,
	# not the proxy.

def uncached_in_response(context):
	"""
	Cause the `context` value to not be cacheable when used in a Pyramid
	response.

	Because the context object is likely to be persistent, this uses a
	proxy and causes the proxy to also implement
	:class:`nti.appserver.interfaces.IUncacheableInResponse`
	"""
	return context if IUncacheableInResponse.providedBy(context) else _UncacheableInResponseProxy(context)
