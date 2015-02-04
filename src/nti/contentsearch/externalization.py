#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search externalization

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO

from .interfaces import ISearchHitMetaData

@interface.implementer(IInternalObjectIO)
@component.adapter(ISearchHitMetaData)
class _SearchHitMetaDataExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = ISearchHitMetaData

@interface.implementer(IInternalObjectIO)
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

@interface.implementer(IInternalObjectIO)
class _SearchResultsInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	_excluded = {'ContentHits', 'UserDataHits'}
	_excluded_out_ivars_ = _excluded | AutoPackageSearchingScopedInterfaceObjectIO._excluded_out_ivars_
	_excluded_in_ivars_ = _excluded | AutoPackageSearchingScopedInterfaceObjectIO._excluded_in_ivars_

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
		return (search_interfaces.ISearchResults,
				search_interfaces.ISuggestResults,
				search_interfaces.ISuggestAndSearchResults)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('search_results',)

_SearchResultsInternalObjectIO.__class_init__()
