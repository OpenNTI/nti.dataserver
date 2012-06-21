#!/usr/bin/env python
"""
Implementations and support for question parts.
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component
from dm.zope.schema.schema import SchemaConfigured

from nti.externalization.externalization import make_repr

from nti.assessment import interfaces
from nti.assessment.interfaces import convert_response_for_solution

from persistent import Persistent



class QPart(SchemaConfigured,Persistent):
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
	explanation = ''

	def grade( self, response ):
		for solution in self.solutions:
			# Graders return a true or false value. We are responsible
			# for applying weights to that
			result = self._grade( solution, convert_response_for_solution( solution, response ) )
			if result:
				return 1.0 * solution.weight
		return 0.0

	def _grade(self, solution, response):
		grader = component.getMultiAdapter( (self, solution, response),
											self.grader_interface,
											name=self.grader_name	)
		return grader()

	__repr__ = make_repr()

	def __eq__( self, other ):
		try:
			return self is other or (self.content == other.content
									 and self.hints == other.hints
									 and self.solutions == other.solutions
									 and self.explanation == other.explanation )
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		return not (self == other is True)

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

	def __eq__( self, other ):
		try:
			return self is other or (super(QMultipleChoicePart,self).__eq__( other ) is True and self.choices == other.choices )
		except AttributeError:
			return NotImplemented

@interface.implementer(interfaces.IQMatchingPart)
class QMatchingPart(QPart):

	grader_interface = interfaces.IQMatchingPartGrader

	labels = ()
	values = ()

	def __eq__( self, other ):
		try:
			return self is other or (super(QMatchingPart,self).__eq__( other ) is True and self.labels == other.labels and self.values == other.values )
		except AttributeError:
			return NotImplemented

@interface.implementer(interfaces.IQFreeResponsePart)
class QFreeResponsePart(QPart):
	pass
