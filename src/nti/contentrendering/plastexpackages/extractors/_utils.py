#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from plasTeX.Renderers import render_children

def _render_children(renderer, nodes, strip=False):
    if not isinstance(nodes, six.string_types):
        result = unicode(''.join(render_children(renderer, nodes)))
    else:
        result = nodes.decode("utf-8") if isinstance(nodes, bytes) else nodes
    return result.strip() if strip and result else result