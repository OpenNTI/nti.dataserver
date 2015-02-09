#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Concept tagging module

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from . import interfaces as ct_interfaces

def concept_tag(content, name=u''):
	tagger = component.getUtility(ct_interfaces.IConceptTagger, name=name)
	result = tagger(content)
	return result
