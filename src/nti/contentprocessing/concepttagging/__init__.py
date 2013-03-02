# -*- coding: utf-8 -*-
"""
Concept tagging module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from . import interfaces as cpct_interfaces

def concept_tag(content, name=u''):
	tagger = component.getUtility(cpct_interfaces.IConceptTagger, name=name)
	result = tagger(content)
	return result
