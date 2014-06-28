#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: too many ancestors
# pylint: disable=I0011,R0901

from zope import schema

from nti.schema.field import Object
from nti.schema.field import List

####
# External client preferences
####

from zope.location.interfaces import ILocation
from nti.dataserver.interfaces import ILastModified

from dolmen.builtins import IUnicode


class IContentUnitPreferences(ILocation,
							  ILastModified):
	"""
	Storage location for preferences related to a content unit.
	"""
	# NOTE: This can actually be None in some cases, which makes it
	# impossible to validate this schema.
	sharedWith = List( value_type=Object(IUnicode),
					   title="List of usernames to share with" )
