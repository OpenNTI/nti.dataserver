#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters commonly useful during various rendering pipelines.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.dataserver.interfaces import ITitledContent
from nti.dataserver.interfaces import IUser
from nti.dataserver.users.interfaces import IFriendlyNamed

from pyramid.interfaces import IRequest

from zc.displayname.interfaces import IDisplayNameGenerator
from zc.displayname.adapters import DefaultDisplayNameGenerator
from zc.displayname.adapters import convertName

@interface.implementer(IDisplayNameGenerator)
@component.adapter(IUser,IRequest)
class UserDisplayNameGenerator(object):
	"""
	Get the display name for a user.
	"""
	def __init__(self, context, request):
		self.context = context

	def __call__(self, maxlength=None):
		names = IFriendlyNamed(self.context)
		return names.alias or names.realname or self.context.username


@component.adapter(ITitledContent,IRequest)
class TitledContentDisplayNameGenerator(DefaultDisplayNameGenerator):
	"""
	Our :class:`.ITitledDescribedContent` is an implementation of
	:class:`.IDCDescriptiveProperties`, but its superclass,
	:class:`.ITitledContent` is not. This display generator
	fixes that: if the object actually has a title, use it, otherwise,
	let the default kick in (if the object can be adapted to
	``IDCDescriptiveProperties`` use that title, otherwise use the name).
	"""

	def __call__(self, maxlength=None):
		title = getattr(self.context, 'title', None)
		if title:
			return convertName(title, self.request, maxlength)

		return DefaultDisplayNameGenerator.__call__(self, maxlength=maxlength)
