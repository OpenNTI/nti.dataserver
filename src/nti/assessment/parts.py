#!/usr/bin/env python
"""
Implementations and support for question parts.
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.assessment import interfaces
from nti.assessment.interfaces import convert_response_for_solution

from persistent import Persistent



class QPart(Persistent):
	"""
	Base class for parts. Its :meth:`grade` method
	will attempt to transform the input based on the interfaces
	this object implements and then call the :meth:`_grade` method.
	"""

	interface.implements(interfaces.IQPart)

	grader_interface = interfaces.IQPartGrader
	grader_name = ''

	content = ''
	hints = ()
	solutions = ()
	explanation = ()

	def __init__( self, **kwargs ):
		"""
		Accepts keyword arguments corresponding to the attributes
		of the :class:`interfaces.IQPart` interface.
		"""

		for k in kwargs.keys():
			if hasattr(self, k):
				v = kwargs.pop( k )
				if v is not None:
					setattr( self, k, v )
		if kwargs:
			raise ValueError( "Unexpected keyword arguments", kwargs )

	def grade( self, response ):
		for solution in self.solutions:
			result = self._grade( solution, convert_response_for_solution( solution, response ) )
			# TODO: Taking weights into account
			if result:
				return result
		return False

	def _grade(self, solution, response):
		grader = component.getMultiAdapter( (self, solution, response),
											self.grader_interface,
											name=self.grader_name	)
		return grader()

@interface.implementer(interfaces.IQMathPart)
class QMathPart(QPart):
	pass

@interface.implementer(interfaces.IQSymbolicMathPart)
class QSymbolicMathPart(QMathPart):

	grader_interface = interfaces.IQSymbolicMathGrader

@interface.implementer(interfaces.IQNumericMathPart)
class QNumericMathPart(QMathPart):
	pass

@interface.implementer(interfaces.IQMultipleChoicePart)
class QMultipleChoicePart(QPart):

	grader_interface = interfaces.IQMultipleChoicePartGrader
	choices = ()

@interface.implementer(interfaces.IQMatchingPart)
class QMatchingPart(QPart):

	grader_interface = interfaces.IQMatchingPartGrader

	labels = ()
	values = ()

@interface.implementer(interfaces.IQFreeResponsePart)
class QFreeResponsePart(QPart):
	pass
