#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# BWC
from .course import _CourseExtractor
from .media import _NTIAudioExtractor
from .media import _NTIVideoExtractor
from .discussion import _DiscussionExtractor
from .related_work import _RelatedWorkExtractor
