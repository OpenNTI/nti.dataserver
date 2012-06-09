#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines the interfaces that make up the contract of this package.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import schema


class TypedIterable(schema.List):
	"""
	An arbitrary (indexable) iterable, not necessarily a list or tuple.
	The values may be homogeneous by setting the value_type
	"""
	_type = None # Override from super to not force a list


class IRepresentableContentUnit(interface.Interface):
	"""
	Some distinguishable unit of content that can be represented
	for presentation to a human, potentially in multiple ways. (For convenience
	and backwards compatibility, this is often referred to as a "resource".)

	"""

	source = schema.Text( title="The source text that defines the resource.",
						  description="Two resources are equivalent if they have equal sources." )

class IRepresentationPreferences(interface.Interface):
	"""
	Something that expresses a preference about the way it is represented
	to the user.
	"""

	resourceTypes = TypedIterable( title="Ordered list of preferred representation formats.",
								   value_type=schema.TextLine(title="Each one is a string naming a format" ) )

class IContentUnitRepresentations(interface.Interface):
	"""
	A collection holding the various representations of a
	particular resource.

	Each representation is unique in the combination of `resourceType`
	and `qualifiers.`
	"""

	source = schema.Text( title="The source text that defines the resource.",
						  description="Copied from the resource. Two resources are equivalent if they have equal sources." )


class IContentUnitRepresentation(interface.Interface):
	"""
	One particular representation of a unit of content.
	"""

	# TODO: Should this be necessary?
	resourceSet = schema.Object( IContentUnitRepresentations,
								 title="The collection of representations holding this representation.")

	source = schema.Text( title="The source text that defines the resource.",
						  description="Copied from the resource. Two resources are equivalent if they have equal sources." )

	resourceType = schema.TextLine( title="The primary type (e.g., png) of this representation" )
	qualifiers = schema.Iterable( title="Additional qualifiers providing refining details of this representation.",
								  description="Generally these will be strings; they all have equal priority, and order doesn't matter" )

class IContentUnitRepresentationBatchConverter(interface.Interface):
	"""
	Something that can produce :class:`IContentUnitRepresentation` objects
	of a particular format in a batch process.
	"""

	resourceType = schema.TextLine( title="The primary type of the representations this object produces." )

	def process_batch( content_units ):
		"""
		:param content_units: A sequence of :class:`IRepresentableContentUnit` objects
		:return: A sequence of :class:`IContentUnitRepresentation` objects corresponding
			to the transformed source of the given content units. This may produce several
			variants of each content unit, corresponding to multiple returned objects with the same
			`source` and `resourceType` but different `qualifiers.`
		"""

class IContentUnitRepresentationBatchCompilingConverter(IContentUnitRepresentationBatchConverter):
	"""
	A specialized converter that drives an *external* compiler programe to convert
	batches of content unit into representations.
	"""

	compiler = schema.ASCIILine( title="The program name of the compiler command to execute." )


class IFilesystemContentUnitRepresentation(IContentUnitRepresentation):
	"""
	A representation of the content unit that has been stored in the filesystem.
	"""

	path = schema.TextLine( title="The path on disk of the file for this representation." )
