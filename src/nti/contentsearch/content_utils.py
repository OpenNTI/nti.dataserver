#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.base._compat import text_

from nti.contentprocessing import tokenize_content
from nti.contentprocessing import get_content_translation_table


def get_content(text=None, language='en'):
    result = ()
    text = text_(text) if text else None
    if text:
        table = get_content_translation_table(language)
        result = tokenize_content(text.translate(table), language)
    result = u' '.join(result)
    return text_(result)
