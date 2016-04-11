#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for reading and setting Dublin Core metadata.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope.dublincore import xmlmetadata

from zope.dublincore.annotatableadapter import partialAnnotatableAdapterFactory

from zope.dublincore.interfaces import IWriteZopeDublinCore

from nti.contentlibrary.interfaces import IDelimitedHierarchyKey

#: An optional XML file containing Dublin Core metadata to be associated
#: with the content package
DCMETA_FILENAME = 'dc_metadata.xml'

# For weird reasons I don't understand, Creator and Subject are supposed
# to be callable objects that are singleton, whereas Contributors is kept
# upper case and as-is (although in the XML it will come in as Contributor).
# So we have a partial mapping to fix this (the things in zope.dublincore.dcterms
# aren't sufficient)
_xml_to_attr = { 'Creator': 'creators',
				 'Contributor': 'contributors',
				 'Subject': 'subjects',
				 'Title': 'title',
				 'Description': 'description'}
_scalars = {'Title', 'Description'}

def read_dublincore_from_source(dublin_object, source, lastModified=None):
	dublin_properties = IWriteZopeDublinCore(dublin_object, None)
	if dublin_properties is None:
		return

	lastModified = time.time() if lastModified is None else lastModified

	# While we'd like to read from the file directly for better
	# errors,, it turns out that this triggers a codepath in
	# xml.sax that tries to resolve DTDs externally across HTTP, which we
	# don't really want. There's no trivial way to customize this.
	metadata = xmlmetadata.parseString(source)

	# Most implementations use an underlying dictionary that's supposed
	# to track with what the metadata produces. If we don't know a property
	# to map to, and we can go to the map, we do
	core_mapping = getattr(dublin_properties, '_mapping', None)

	for k in metadata:
		if k in _xml_to_attr:
			val = metadata[k]
			if k in _scalars:
				val = val[0]
			setattr(dublin_properties, str(_xml_to_attr[k]), val)
		elif core_mapping is not None:
			core_mapping[k] = metadata[k]
		else:
			if k[0].isUpper():
				k = k.lower()
			setattr(dublin_properties, str(k), metadata[k])

	# Annotation-based instances may not actually store anything until
	# after _changed is called, but we have to be sure we keep a modified
	# time
	try:
		dublin_properties._changed()
		core_mapping.lastModified = lastModified
	except AttributeError:
		pass
	dublin_properties.lastModified = lastModified

	return dublin_properties

def read_dublincore_from_named_key(dublin_object, bucket, 
								   filename=DCMETA_FILENAME, force=False):
	dublin_key = bucket.getChildNamed(DCMETA_FILENAME)
	if not IDelimitedHierarchyKey.providedBy(dublin_key):
		return

	dublin_properties = IWriteZopeDublinCore(dublin_object, None)
	if dublin_properties is None:
		return

	if not force and dublin_key.lastModified <= getattr(dublin_properties, 'lastModified', 0):
		return

	source = dublin_key.readContents()
	result = read_dublincore_from_source(dublin_object, source, dublin_key.lastModified)
	return result

#: A standard adapter for the content packages and bundles
#: defined in this package (things that implement IDisplayableContent)
#: and thus have their own attributes
DisplayableContentZopeDublinCoreAdapter = partialAnnotatableAdapterFactory(
	map(str,
		# IDCDescriptiveProperties
		['title', 'description',
		 # IDCExtended.
		 'publisher'
		 # Sadly, the sequence properties aren't supported directly
		 # for some reason, so we do that ourself.
		 # TODO: Submit pull request
		 # 'creators', 'subjects', 'contributors'
	 ]))

class _SequenceDirectProperty(object):
	def __init__(self, name, attrname):
		self.__name__ = name
		self.__attrname = str(attrname)

	def __get__(self, inst, klass):
		if inst is None:
			return self
		context = inst._ZDCPartialAnnotatableAdapter__context
		return getattr(context, self.__attrname, ())

	def __set__(self, inst, value):
		# Match what the normal SequencProperty does
		value = tuple(value)
		for v in value:
			if not isinstance(v, unicode):
				raise TypeError("Elements must be unicode")
		context = inst._ZDCPartialAnnotatableAdapter__context
		oldvalue = getattr(context, self.__attrname, None)
		if oldvalue != value:
			setattr(context, self.__attrname, value)

for x in map(str, ['creators', 'subjects', 'contributors']):
	prop = _SequenceDirectProperty(x, x)
	setattr(DisplayableContentZopeDublinCoreAdapter, x, prop)

#: A standard adapter for things that are just descriptive properties
#: but also annotatable
DescriptivePropertiesZopeDublinCoreAdapter = partialAnnotatableAdapterFactory(
	map(str,
		['title', 'description']))

# Both of them need a way to store last Modified, since the object is created on demand
# (only the mapping is persistent)

class _LastModifiedProperty(object):

	def __init__(self):
		pass

	def __get__(self, inst, klass):
		if inst is None:
			return self
		return getattr(inst._mapping, 'lastModified', 0)

	def __set__(self, inst, value):
		inst._mapping.lastModified = value

DisplayableContentZopeDublinCoreAdapter.lastModified = _LastModifiedProperty()
DescriptivePropertiesZopeDublinCoreAdapter.lastModified = _LastModifiedProperty()
