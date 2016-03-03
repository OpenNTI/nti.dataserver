#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.contentlibrary.indexed_data.interfaces import INTIIDAdapter
from nti.contentlibrary.indexed_data.interfaces import INamespaceAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainedTypeAdapter

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

from nti.zope_catalog.index import SetIndex as RawSetIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex

def to_iterable(value):
	if isinstance(value, (list, tuple, set)):
		result = value
	else:
		result = (value,) if value is not None else ()
	result = tuple(getattr(x, '__name__', x) for x in result)
	return result

class RetainSetIndex(RawSetIndex):
	"""
	A set index that retains the old values.
	"""

	def to_iterable(self, value=None):
		result = to_iterable(value)
		return result

	def index_doc(self, doc_id, value):
		value = {v for v in self.to_iterable(value) if v is not None}
		old = self.documents_to_values.get(doc_id) or set()
		if value.difference(old):
			value.update(old or ())
			result = super(RetainSetIndex, self).index_doc(doc_id, value)
			return result

	def remove(self, doc_id, value):
		old = set(self.documents_to_values.get(doc_id) or ())
		if not old:
			return
		for v in to_iterable(value):
			old.discard(v)
		if old:
			super(RetainSetIndex, self).index_doc(doc_id, old)
		else:
			super(RetainSetIndex, self).unindex_doc(doc_id)

class ValidatingSiteName(object):

	__slots__ = (b'site',)

	def __init__(self, obj, default=None):
		folder = find_interface(obj, IHostPolicyFolder, strict=False)
		if folder is not None:
			self.site = folder.__name__

	def __reduce__(self):
		raise TypeError()

class SiteIndex(ValueIndex):
	default_field_name = 'site'
	default_interface = ValidatingSiteName

class TypeIndex(ValueIndex):
	default_field_name = 'type'
	default_interface = IContainedTypeAdapter
	
class NamespaceIndex(ValueIndex):
	default_field_name = 'namespace'
	default_interface = INamespaceAdapter

class NTIIDIndex(ValueIndex):
	default_field_name = 'ntiid'
	default_interface = INTIIDAdapter
