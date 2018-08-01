#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.base._compat import text_

from nti.contentprocessing.content_utils import tokenize_content
from nti.contentprocessing.content_utils import get_content_translation_table

logger = __import__('logging').getLogger(__name__)


def get_content(text=None, language='en'):
    result = ()
    text = text_(text) if text else None
    if text:
        table = get_content_translation_table(language)
        result = tokenize_content(text.translate(table), language)
    result = u' '.join(result)
    return text_(result)
