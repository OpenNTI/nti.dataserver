#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Abstract classes to be used as pyramid view callables.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

from zope import component
from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.intid.interfaces import IIntIds

from zope.proxy import ProxyBase

from nti.app.authentication import get_remote_user as _get_remote_user

from nti.common.property import Lazy
from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.interfaces import IDataserver

from .interfaces import IMultipartSource

def _check_creator(remote_user, obj):
	result = False
	try:
		if remote_user == obj.creator:
			result = True
	except AttributeError:
		pass
	return result

def _check_dynamic_memberships(remote_user, obj):
	family = component.getUtility(IIntIds).family
	my_ids = remote_user.xxx_intids_of_memberships_and_self
	result = False
	try:
		if obj.xxx_isReadableByAnyIdOfUser(remote_user, my_ids, family):
			result = True
	except (AttributeError, TypeError):
		pass
	return result

def _check_shared_with(remote_user, obj):
	result = False
	try:
		if obj.isSharedWith(remote_user):
			result = True
	except (AttributeError, TypeError):
		pass
	return result

def make_sharing_security_check(request, remoteUser):
	"""
	Return a callable object of one argument that returns true if the
	argument is readable to the current remote user.

	Note that this is *NOT* a full ACL or security policy check, it is optimized
	for speed and should only be used with a set of objects for which we know
	the sharing model is appropriate. (We do fall back to the full security
	check if all our attempts to determine sharing fail.)

	As an implementation details, if the ``isSharedWith`` method, used in the general
	case, is known to be slow, a method called ``xxx_isReadableByAnyIdOfUser``
	that takes three arguments (remote user, the intids of the current user and
	his memberships, and the BTree family of these sets) can be defined instead.
	(The intids of the user and his memberships are defined in another
	private property ``xxx_intids_of_memberships_and_self`` defined elsewhere.)
	"""

	remote_request = request

	# XXX Deferred import to avoid a cycle. This will move to an nti.app
	# package, and this entire method may move with it too.
	from nti.appserver.pyramid_authorization import is_readable

	def security_check(x):
		# 1. Creator
		# 2. Dynamic memberships
		# 3. SharedWith
		# 4. ACL
		return 	_check_creator(remoteUser, x) \
			or	_check_dynamic_memberships(remoteUser, x) \
			or	_check_shared_with(remoteUser, x) \
			or 	is_readable(x, remote_request)
	return security_check

class AbstractView(object):
	"""
	Base class for views. Defines the ``request``, ``context`` and ``dataserver``
	properties. To be a valid view callable, you must implement ``__call__``.
	"""

	def __init__(self, request):
		self.request = request

	@Lazy
	def context(self):
		return self.request.context

	@Lazy
	def dataserver(self):
		return component.getUtility(IDataserver)

class AuthenticatedViewMixin(object):
	"""
	Mixin class for views that expect to be authenticated.
	"""

	def getRemoteUser(self):
		"""
		Returns the user object corresponding to the currently authenticated
		request.
		"""
		return _get_remote_user(self.request, self.dataserver)

	@Lazy
	def remoteUser(self):
		"""
		Returns the remote user for the current request; cached on first use.
		"""
		return self.getRemoteUser()

	def make_sharing_security_check(self):
		result = make_sharing_security_check(self.request, self.remoteUser)
		return result

class AbstractAuthenticatedView(AbstractView, AuthenticatedViewMixin):
	"""
	Base class for views that expect authentication to be required.
	"""

@interface.implementer(IMultipartSource)
class SourceProxy(ProxyBase):

	length = property(lambda s: s.__dict__.get('_v_length'),
					  lambda s, v: s.__dict__.__setitem__('_v_length', v))

	contentType = property(
					lambda s: s.__dict__.get('_v_content_type'),
					lambda s, v: s.__dict__.__setitem__('_v_content_type', v))

	filename = property(
					lambda s: s.__dict__.get('_v_filename'),
					lambda s, v: s.__dict__.__setitem__('_v_filename', v))

	def __new__(cls, base, *args, **kwargs):
		return ProxyBase.__new__(cls, base)

	def __init__(self, base, filename=None, contentType=None, length=None):
		ProxyBase.__init__(self, base)
		self.filename = filename
		self.contentType = contentType
		self.length = length

	@readproperty
	def mode(self):
		return "rb"

	@property
	def size(self):
		return self.length

	def getSize(self):
		return self.size

def _get_file_size( source ):
	return os.fstat( source.file.fileno() ).st_size

def process_source(source, default_content_type=u'application/octet-stream'):
	if isinstance(source, six.string_types):
		length = len(source)
		source = StringIO(source)
		source.seek(0)
		source = SourceProxy(source, content_type='application/json', length=length)
	elif source is not None:
		length = getattr(source, 'length', None)
		if not length or length == -1:
			length = _get_file_size( source )
		filename = getattr(source, 'filename', None)
		contentType = ( 	getattr(source, 'type', None)
						or	getattr(source, 'contentType', None) )
		contentType = contentType or default_content_type
		source = source.file
		source.seek(0)
		source = SourceProxy(source, filename, contentType, length)
	return source

def get_source(request, *keys):
	source = None
	values = CaseInsensitiveDict(request.POST)
	for key in keys:
		source = values.get(key)
		if source is not None:
			break
	source = process_source(source)
	return source

def get_all_sources(request, default_content_type=u'application/octet-stream'):
	result = CaseInsensitiveDict()
	values = CaseInsensitiveDict(request.POST)
	for name, source in values.items():
		try:
			source = process_source(source, default_content_type)
		except AttributeError:
			continue
		result[name] = source
	return result
