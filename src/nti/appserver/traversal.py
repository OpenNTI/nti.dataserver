#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for resource tree traversal.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.deferredimport import deprecatedFrom
deprecatedFrom("Prefer nti.traversal.traversal",
               "nti.traversal.traversal",
               "resource_path",
               "normal_resource_path")
