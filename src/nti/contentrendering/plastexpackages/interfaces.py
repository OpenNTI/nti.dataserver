#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces related to packages used for plasTeX processing.
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from nti.contentrendering import interfaces as cdr_interfaces

class IAssessmentExtractor(cdr_interfaces.IRenderedBookTransformer):
	"""
	Looks through the rendered book and extracts assessment information.
	"""
