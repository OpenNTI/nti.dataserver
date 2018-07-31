#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO


class _SearchHitInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

    _excluded_in_ivars_ = {'Query'}
    _excluded_out_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_out_ivars_

    @classmethod
    def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
        return (search_interfaces.ISearchHit,)

    @classmethod
    def _ap_enumerate_module_names(cls):
        return ('search_hits',)

_SearchHitInternalObjectIO.__class_init__()
