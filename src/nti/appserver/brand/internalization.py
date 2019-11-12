#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from persistent.mapping import PersistentMapping

from zope import component
from zope import interface

from nti.appserver.brand.interfaces import ISiteBrand

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater

logger = __import__('logging').getLogger(__name__)


@component.adapter(ISiteBrand)
@interface.implementer(IInternalObjectUpdater)
class _SiteBrandUpdater(InterfaceObjectIO):

    _ext_iface_upper_bound = ISiteBrand

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        """
        Make sure we store these objects in the type we choose.
        """
        has_theme = 'theme' in parsed
        theme_ext = parsed.pop('theme', {})
        result = super(_SiteBrandUpdater, self).updateFromExternalObject(parsed, *args, **kwargs)

        if has_theme:
            if self._ext_self._theme is None:
                self._ext_self._theme = PersistentMapping()
            self._ext_self._theme.clear()
            self._ext_self._theme.update(theme_ext)
            result = True
        return result
