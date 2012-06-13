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
	# Strip off 'IQ' if it's not 'IQuestionXYZ'
	return iface.__name__[2:] if not iface.__name__.startswith( 'IQuestion' ) else iface.__name__[1:]

def _apply_tagged_values():
	for iface in (asm_interfaces.IQPart, asm_interfaces.IQuestion, asm_interfaces.IQSolution,
				  asm_interfaces.IQuestionSubmission, asm_interfaces.IQAssessedPart, asm_interfaces.IQAssessedQuestion,
				  asm_interfaces.IQuestionSetSubmission, asm_interfaces.IQAssessedQuestionSet):
		iface.setTaggedValue( '__external_class_name__', _external_class_name_ )
_apply_tagged_values()
