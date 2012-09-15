#!/usr/bin/env python
"""
Definition of the redaction object.
"""

from __future__ import print_function, unicode_literals

from nti.dataserver import interfaces as nti_interfaces

from zope import interface

from .highlight import SelectedRange

@interface.implementer(nti_interfaces.IRedaction)
class Redaction(SelectedRange):

	replacementContent = None
	redactionExplanation = None
	_schema_fields_to_validate_ = SelectedRange._schema_fields_to_validate_ + ('replacementContent','redactionExplanation')
	_schema_to_validate_ = nti_interfaces.IRedaction
