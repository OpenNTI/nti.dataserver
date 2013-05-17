# -*- coding: utf-8 -*-
"""
QTI Parser

$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

# from lxml import etree
from io import BytesIO

def parser(source):
	source = BytesIO(source) if not hasattr(source, 'read') else source
	# root = etree.parse(source)

