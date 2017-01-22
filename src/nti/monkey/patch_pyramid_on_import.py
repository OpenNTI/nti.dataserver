#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import pkg_resources

dist = pkg_resources.get_distribution('pyramid')
if not dist.version or dist.version == '1.8':
    import pyramid.config
    from pyramid.asset import resolve_asset_spec
    from pyramid.config import Configurator

    class _Configuratory(Configurator):

        def _split_spec(self, path_or_spec):
            return resolve_asset_spec(path_or_spec, self.package_name)

    pyramid.config.Configurator = _Configuratory


def patch():
    pass
