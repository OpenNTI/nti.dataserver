#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO

logger = __import__('logging').getLogger(__name__)


class _SearchHitInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

    _excluded_in_ivars_ = {'Query'}
    _excluded_out_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_out_ivars_

    @classmethod
    # pylint: disable=arguments-differ
    def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
        return (search_interfaces.ISearchHit,)

    @classmethod
    def _ap_enumerate_module_names(cls):
        return ('search_hits',)

_SearchHitInternalObjectIO.__class_init__()
