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
from zope.dottedname import resolve as dottedname

from nti.assessment import interfaces as asm_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import ModuleScopedInterfaceObjectIO
from nti.externalization.internalization import register_legacy_search_module

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
				  asm_interfaces.IQuestionSetSubmission, asm_interfaces.IQAssessedQuestionSet,
				  asm_interfaces.IQHint, asm_interfaces.IQuestionSet):
		iface.setTaggedValue( '__external_class_name__', _external_class_name_ )
_apply_tagged_values()

class _ClassNameRegistry(object): pass

def _find_factories():

	for mod_name in ('hint', 'assessed', 'parts', 'question', 'response', 'solution', 'submission'):
		mod = dottedname.resolve( 'nti.assessment.' + mod_name )
		for k, v in mod.__dict__.items():
			if getattr( v, '__module__', None) != mod.__name__ or type(v) != type:
				continue
			# Does this implement something that should be externalizable?
			# If so, register it, chopping off the leading 'Q'
			if any( (iface.queryTaggedValue( '__external_class_name__') for iface in interface.implementedBy(v)) ):
				ext_class_name = k[1:] if not k.startswith( 'Question' ) else k
				setattr( _ClassNameRegistry, ext_class_name, v )
				if not 'mime_type' in v.__dict__:
					# NOT hasattr. We don't use hasattr because inheritance would
					# throw us off. It could be something we added, and iteration order
					# is not defined (if we got the subclass first we're good, we fail if we
					# got superclass first)
					setattr( v, 'mime_type', 'application/vnd.nextthought.assessment.' + ext_class_name.lower() )

				# Opt in for creating, unless explicitly disallowed
				if not hasattr( v, '__external_can_create__' ):
					setattr( v, '__external_can_create__', True )
					# Let them have containers
					if not hasattr( v, 'containerId' ):
						setattr( v, 'containerId', None )
_find_factories()
register_legacy_search_module( _ClassNameRegistry )
