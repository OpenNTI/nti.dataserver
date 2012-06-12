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
