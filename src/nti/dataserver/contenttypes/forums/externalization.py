#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization for forum objects.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO

from ..base import UserContentRootInternalObjectIOMixin

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _ForumInternalObjectIO(UserContentRootInternalObjectIOMixin,AutoPackageSearchingScopedInterfaceObjectIO):

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces( cls, frm_interfaces ):
		return (frm_interfaces.IBoard, frm_interfaces.ITopic, frm_interfaces.IForum, frm_interfaces.IPost)

	@classmethod
	def _ap_enumerate_module_names( cls ):
		return ('board', 'forum', 'post', 'topic')

_ForumInternalObjectIO.__class_init__()

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _ForumACEInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, frm_interfaces):
		return (frm_interfaces.IForumACE,)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('ace',)

_ForumACEInternalObjectIO.__class_init__()
