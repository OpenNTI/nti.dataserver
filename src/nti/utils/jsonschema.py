#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
For producing a JSON schema appropriate for use by clients, based on a Zope schema.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deprecation
zope.deprecation.moved('nti.schema.jsonschema')