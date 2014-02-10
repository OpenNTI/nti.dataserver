#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO

from . import interfaces as search_interfaces

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(search_interfaces.ISearchHitMetaData)
class _SearchHitMetaDataExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = search_interfaces.ISearchHitMetaData

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _SearchHitInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	_excluded_out_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_out_ivars_
	_excluded_in_ivars_ = {'Query'}

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
		return (search_interfaces.ISearchHit,)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('search_hits',)

_SearchHitInternalObjectIO.__class_init__()

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _SearchResultsInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
		return (search_interfaces.ISearchResults,
				search_interfaces.ISuggestResults,
				search_interfaces.ISuggestAndSearchResults)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('search_results',)

_SearchResultsInternalObjectIO.__class_init__()
