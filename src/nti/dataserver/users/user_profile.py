#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of user profile related storage.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
import zope.location.interfaces
import zope.annotation

import persistent

from zope.schema.fieldproperty import FieldPropertyStoredThroughField

from nti.dataserver import interfaces as nti_interfaces
from . import interfaces

@component.adapter(nti_interfaces.IUser)
@interface.implementer(interfaces.ICompleteUserProfile,zope.location.interfaces.ILocation)
class CompleteUserProfile(persistent.Persistent):
	"""
	An adapter for storing profile data for users. Intended to be an annotation, used with
	an annotation factory; in this way we keep the context as our parent, but taket
	it as an optional argument for ease of testing.
	"""

	__parent__ = None
	__name__ = None

	def __init__( self, context=None ):
		super(CompleteUserProfile,self).__init__()
		if context:
			self.__parent__ = context

	@property
	def context(self):
		return self.__parent__

	@property
	def avatarURL(self):
		return interfaces.IAvatarURL(self.context).avatarURL

for _x in interfaces.ICompleteUserProfile.names():
	if not hasattr( CompleteUserProfile, _x ):
		setattr( CompleteUserProfile, _x, FieldPropertyStoredThroughField( interfaces.ICompleteUserProfile[_x] ) )

CompleteUserProfileFactory = zope.annotation.factory( CompleteUserProfile )
