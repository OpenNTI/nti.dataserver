#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization for assessment objects.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface

from nti.assessment import interfaces as asm_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import ModuleScopedInterfaceObjectIO

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _AssessmentInternalObjectIO(ModuleScopedInterfaceObjectIO):

	_ext_search_module = asm_interfaces

# Assign external class names to the root classes

def _external_class_name_( iface, impl ):
	# Strip off 'IQ'
	return iface.__name__[2:]

for iface in (asm_interfaces.IQPart, asm_interfaces.IQuestion, asm_interfaces.IQSolution):
	iface.setTaggedValue( '__external_class_name__', _external_class_name_ )
