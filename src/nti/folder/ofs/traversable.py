#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Based on Zope2.OFS.Traversable

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from urllib import quote

from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from Acquisition import aq_acquire

from Acquisition import Acquired
from Acquisition.interfaces import IAcquirer

from zope.interface import implementer

from zope.location.interfaces import LocationError

from zope.traversing.namespace import nsParse
from zope.traversing.namespace import namespaceLookup

from ZODB.POSException import ConflictError

from .interfaces import ITraversable

_marker = object()

class NotFound(Exception):
	pass

@implementer(ITraversable)
class Traversable(object):

	def absolute_url(self, relative=0):
		"""
		Return the absolute URL of the object.

		This a canonical URL based on the object's physical
		containment path.  It is affected by the virtual host
		configuration, if any, and can be used by external
		agents, such as a browser, to address the object.

		If the relative argument is provided, with a true value, then
		the value of virtual_url_path() is returned.

		Some Products incorrectly use '/'+absolute_url(1) as an
		absolute-path reference.  This breaks in certain virtual
		hosting situations, and should be changed to use
		absolute_url_path() instead.
		"""
		if relative:
			return self.virtual_url_path()

		spp = self.getPhysicalPath()

		try:
			toUrl = aq_acquire(self, 'REQUEST').physicalPathToURL
		except AttributeError:
			return path2url(spp[1:])
		return toUrl(spp)

	def absolute_url_path(self):
		"""
		Return the path portion of the absolute URL of the object.

		This includes the leading slash, and can be used as an
		'absolute-path reference' as defined in RFC 2396.
		"""
		spp = self.getPhysicalPath()
		try:
			toUrl = aq_acquire(self, 'REQUEST').physicalPathToURL
		except AttributeError:
			return path2url(spp) or '/'
		return toUrl(spp, relative=1) or '/'

	def virtual_url_path(self):
		"""
		Return a URL for the object, relative to the site root.

		If a virtual host is configured, the URL is a path relative to
		the virtual host's root object.  Otherwise, it is the physical
		path.  In either case, the URL does not begin with a slash.
		"""
		spp = self.getPhysicalPath()
		try:
			toVirt = aq_acquire(self, 'REQUEST').physicalPathToVirtualPath
		except AttributeError:
			return path2url(spp[1:])
		return path2url(toVirt(spp))

	getPhysicalRoot = Acquired

	def getPhysicalPath(self):
		"""
		Get the physical path of the object.

		Returns a path (an immutable sequence of strings) that can be used to
		access this object again later, for example in a copy/paste operation.
		getPhysicalRoot() and getPhysicalPath() are designed to operate
		together.
		"""
		path = (self.getId(),)

		p = aq_parent(aq_inner(self))
		if p is not None:
			path = p.getPhysicalPath() + path
		return path

	def unrestrictedTraverse(self, path, default=_marker):
		"""
		Lookup an object by path.

		path -- The path to the object. May be a sequence of strings or a slash
		separated string. If the path begins with an empty path element
		(i.e., an empty string or a slash) then the lookup is performed
		from the application root. Otherwise, the lookup is relative to
		self. Two dots (..) as a path element indicates an upward traversal
		to the acquisition parent.

		default -- If provided, this is the value returned if the path cannot
		be traversed for any reason (i.e., no object exists at that path or
		the object is inaccessible).
		"""
		if not path:
			return self

		if isinstance(path, six.string_types):
			# Unicode paths are not allowed
			path = path.split('/')
		else:
			path = list(path)

		path.reverse()
		path_pop = path.pop

		if len(path) > 1 and not path[0]:
			# Remove trailing slash
			path_pop(0)

		if not path[-1]:
			# If the path starts with an empty string, go to the root first.
			path_pop()
			obj = self.getPhysicalRoot()
		else:
			obj = self

		next_ = None
		try:
			while path:
				name = path_pop()
				__traceback_info__ = path, name

				if name[0] == '_':
					# Never allowed in a URL.
					raise NotFound("Not found %s" % name)

				if name == '..':
					next_ = aq_parent(obj)
					if next_ is not None:
						obj = next_
						continue

				try:
					if name and name[:1] in '@+' and name != '+' and nsParse(name)[1]:
						# Process URI segment parameters.
						ns, nm = nsParse(name)
						try:
							next_ = namespaceLookup(
										ns, nm, obj, aq_acquire(self, 'REQUEST'))
							if IAcquirer.providedBy(next_):
								next_ = next_.__of__(obj)
						except LocationError:
							raise AttributeError(name)
					else:
						if getattr(aq_base(obj), name, _marker) is not _marker:
							next_ = getattr(obj, name)
						else:
							try:
								next_ = obj[name]
							except (AttributeError, TypeError):
								# Raise NotFound for easier debugging
								# instead of AttributeError: __getitem__
								# or TypeError: not subscriptable
								raise NotFound(name)
				except (AttributeError, NotFound, KeyError), e:
					if next_ is not None:
						raise e
					else:
						# try acquired attributes
						try:
							next_ = getattr(obj, name, _marker)
						except AttributeError:
							raise e
						if next_ is _marker:
							# Nothing found re-raise error
							raise e
				obj = next_

			return obj

		except ConflictError:
			raise
		except:
			if default is not _marker:
				return default
			else:
				raise

	restrictedTraverse = unrestrictedTraverse

def path2url(path):
	return '/'.join(map(quote, path))
