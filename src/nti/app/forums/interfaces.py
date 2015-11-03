#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.namedfile.interfaces import IFileConstraints

from nti.schema.field import Int

class IPostFileConstraints(IFileConstraints):
    max_files = Int(title="max attachments files", required=True, default=1)
