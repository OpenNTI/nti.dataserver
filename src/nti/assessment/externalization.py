#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization for assessment objects.

$Id$
"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )


from zope import interface


from nti.externalization import interfaces as ext_interfaces
from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO


@interface.implementer(ext_interfaces.IInternalObjectIO)
class _AssessmentInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	@classmethod
	def _ap_compute_external_class_name_from_interface_and_instance( cls, iface, impl ):
		# Strip off 'IQ' if it's not 'IQuestionXYZ'
		return iface.__name__[2:] if not iface.__name__.startswith( 'IQuestion' ) else iface.__name__[1:]


	@classmethod
	def _ap_compute_external_class_name_from_concrete_class( cls, a_type ):
		k = a_type.__name__
		ext_class_name = k[1:] if not k.startswith( 'Question' ) else k
		return ext_class_name

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces( cls, asm_interfaces ):
		return (asm_interfaces.IQPart, asm_interfaces.IQuestion, asm_interfaces.IQSolution,
				asm_interfaces.IQuestionSubmission, asm_interfaces.IQAssessedPart, asm_interfaces.IQAssessedQuestion,
				asm_interfaces.IQuestionSetSubmission, asm_interfaces.IQAssessedQuestionSet,
				asm_interfaces.IQHint, asm_interfaces.IQuestionSet)

	@classmethod
	def _ap_enumerate_module_names( cls ):
		return ('hint', 'assessed', 'parts', 'question', 'response', 'solution', 'submission')

_AssessmentInternalObjectIO.__class_init__()
