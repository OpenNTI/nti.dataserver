#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to enclosures.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.interfaces import INameChooser

from zope.mimetype.interfaces import IContentTypeAware

from nti.containers.containers import CaseInsensitiveLastModifiedBTreeContainer

from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import IEnclosedContent

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.oids import to_external_ntiid_oid

from nti.property.property import alias

@interface.implementer(IEnclosedContent, IContentTypeAware, IZContained)
class SimplePersistentEnclosure(PersistentCreatedModDateTrackingObject):
	"""
	A trivial implementation of a persistent enclosure.
	Real production usage needs much more thought and should
	use Blobs. Consider the :module:`zope.file` package. See also zope.dublincore.
	"""

	creator = None
	createdTime = 0
	lastModified = 0

	_data = None

	__parent__ = None
	__name__ = alias('name')

	def __init__(self, name, data='', mime_type='text/plain'):
		super(SimplePersistentEnclosure, self).__init__()
		self.name = name
		self.mime_type = mime_type
		self.data = data
		# Change default modified time from 0 to now
		self.lastModified = self.createdTime

	mimeType = alias('mime_type')

	def __setstate__(self, state):
		if 'data' in state:
			state['_data'] = state['data']
			del state['data']
		super(SimplePersistentEnclosure, self).__setstate__(state)

	def _get_data(self):
		return self._data
	def _set_data(self, dta):
		if hasattr(dta, '__parent__'):
			dta.__parent__ = self
		self._data = dta
	data = property(_get_data, _set_data)

	@property
	def NTIID(self):
		# If we wrap something with an NTIID, we want to be treated like it
		result = getattr(self.data, 'NTIID', None)
		if not result:
			result = to_external_ntiid_oid(self)
		return result

from zope.location import locate

class SimpleEnclosureMixin(object):
	"""
	Provides a basic level of support for enclosures to any object.

	Operates by using an instance variable, `_enclosures` to store a
	:class:`.IContainer` of names to enclosures.
	"""

	_enclosures = None

	def __init__(self, *args, **kwargs):
		super(SimpleEnclosureMixin, self).__init__(*args, **kwargs)

	# ## Enclosures
	# The backing store, the _enclosures BTreeContainer, is created
	# on demand

	def _new_enclosure_container(self):
		return CaseInsensitiveLastModifiedBTreeContainer()

	def iterenclosures(self):
		enc = self._enclosures or {}  # In case of None
		return iter(enc.values())

	def add_enclosure(self, content):
		"""
		Adds a new enclosure to this object.

		:param content: An instance of :class:`nti_interfaces.IContent`
			(esp. :class:`nti_interfaces.IEnclosedContent`)
			This method may change the `name` attribute of this object if
			there is already an enclosure with this name, and the enclosure
			container provides an :class:`INameChooser` adapter.
		:raises KeyError: If the enclosures container enforces uniqueness,
			doesn't allow overwriting, and no unique name can be found.
		:raises AttributeError: If the content has no `name` attribute.

		:returns: The content object

		EOD
		"""
		if content is None:
			return None

		if self._enclosures is None:
			self._enclosures = self._new_enclosure_container()
			locate(self._enclosures, self, '++adapter++enclosures')

		enclosures = self._enclosures
		name_chooser = INameChooser(enclosures, None)
		if name_chooser:
			content.name = name_chooser.chooseName(content.name, content)
		enclosures[content.name] = content
		return content

	def get_enclosure(self, name):
		"""
		Return the enclosure with the given name.
		:raises KeyError: If no such enclosure is found.
		"""

		return (self._enclosures or {})[name]

	def del_enclosure(self, name):
		del (self._enclosures or {})[name]
