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
