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
from nti.assessment._util import superhash

from persistent import Persistent


@interface.implementer(interfaces.IQPart)
class QPart(SchemaConfigured,Persistent):
	"""
	Base class for parts. Its :meth:`grade` method
	will attempt to transform the input based on the interfaces
	this object implements and then call the :meth:`_grade` method.
	"""



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
									 and self.explanation == other.explanation
									 and self.grader_interface == other.grader_interface
									 and self.grader_name == other.grader_name)
		except AttributeError: #pragma: no cover
			return NotImplemented

	def __ne__( self, other ):
		return not (self == other is True)

	def __hash__( self ):
		xhash = 47
		xhash ^= hash(self.content)
		xhash ^= superhash(self.hints)
		xhash ^= superhash(self.solutions)
		xhash ^= hash(self.explanation) << 5
		return xhash

@interface.implementer(interfaces.IQMathPart)
class QMathPart(QPart):

	def __eq__( self, other ):
		try:
			return self is other or (isinstance(other,QMathPart)
									 and super(QMathPart,self).__eq__( other ) is True)
		except AttributeError: # pragma: no cover
			return NotImplemented

@interface.implementer(interfaces.IQSymbolicMathPart)
class QSymbolicMathPart(QMathPart):

	grader_interface = interfaces.IQSymbolicMathGrader


	def __eq__( self, other ):
		try:
			return self is other or (isinstance(other,QSymbolicMathPart)
									 and super(QSymbolicMathPart,self).__eq__( other ) is True)
		except AttributeError: # pragma: no cover
			return NotImplemented


@interface.implementer(interfaces.IQNumericMathPart)
class QNumericMathPart(QMathPart):

	def __eq__( self, other ):
		try:
			return self is other or (isinstance(other,QNumericMathPart)
									 and super(QNumericMathPart,self).__eq__( other ) is True)
		except AttributeError: # pragma: no cover
			return NotImplemented

@interface.implementer(interfaces.IQMultipleChoicePart)
class QMultipleChoicePart(QPart):

	grader_interface = interfaces.IQMultipleChoicePartGrader
	choices = ()

	def __eq__( self, other ):
		try:
			return self is other or (isinstance(other,QMultipleChoicePart)
									 and super(QMultipleChoicePart,self).__eq__( other ) is True
									 and self.choices == other.choices )
		except AttributeError: # pragma: no cover
			return NotImplemented

@interface.implementer(interfaces.IQMatchingPart)
class QMatchingPart(QPart):

	grader_interface = interfaces.IQMatchingPartGrader

	labels = ()
	values = ()

	def __eq__( self, other ):
		try:
			return self is other or (isinstance(other, QMatchingPart)
									 and super(QMatchingPart,self).__eq__( other ) is True
									 and self.labels == other.labels
									 and self.values == other.values )
		except AttributeError: #pragma: no cover
			return NotImplemented

@interface.implementer(interfaces.IQFreeResponsePart)
class QFreeResponsePart(QPart):
	def __eq__( self, other ):
		try:
			return self is other or (isinstance(other,QFreeResponsePart)
									 and super(QFreeResponsePart,self).__eq__( other ) is True)
		except AttributeError: # pragma: no cover
			return NotImplemented
