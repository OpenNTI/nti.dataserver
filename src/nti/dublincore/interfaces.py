#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces and support for metadata properties.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from zope.dublincore.interfaces import IDCDescriptiveProperties

from nti.schema.field import Number
from nti.schema.field import ValidText as Text
from nti.schema.field import ValidTextLine as TextLine

class ICreatedTime(interface.Interface):
	"""
	Something that (immutably) tracks its created time.
	"""
	createdTime = Number(title=u"The timestamp at which this object was created.",
						 description="Typically set automatically by the object.",
						 default=0.0)

class ILastModified(ICreatedTime):
	"""
	Something that tracks a modification timestamp.
	"""
	# TODO: Combine/replace this with :class:`zope.dublincore.interfaces.IDCTimes`
	lastModified = Number(title=u"The timestamp at which this object or its contents was last modified.",
						  default=0.0)

class IDCOptionalDescriptiveProperties(IDCDescriptiveProperties):
	"""
	Makes title and description optional.
	"""
	title = TextLine(title="The human-readable section name of this item; alias for `__name__`",
					 default='')  # also defined by IDCDescriptiveProperties as required

	description = Text(title="The human-readable description",
					   default='') # also defined by IDCDescriptiveProperties as required
