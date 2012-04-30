#!/usr/bin/env python
from __future__ import unicode_literals, print_function

from zope import interface
from zope import schema

# TODO: Should the content portions be specifically modelled as
# contentrendering.interfaces.IContentFragment?

class IQHint(interface.Interface):
	"""
	Information intended to help a student complete a question.

	This may have such attributes as 'difficulty' or 'assistance level'.

	It my be inline or be a link (reference) to other content.
	"""

# It seems like the concepts of domain and range may come into play here,
# somewhere

class IQPart(interface.Interface):
	"""
	One generally unnumbered (or only locally numbered) portion of a :class:`Question`
	which requires a response.
	"""

	content = schema.Text( title="The content to present to the user for this portion, if any." )
	hints = schema.Iterable( title="Any hints that pertain to this part" )
	solutions = schema.Iterable( title="Acceptable solutions for this question part in no particular order.",
								description="All solutions must be of the same type, and there must be at least one." )
	explanation = schema.Text( title="An explanation of how the solution is arrived at." )


class IQMathPart(IQPart):
	"""
	A question part whose answer lies in the math domain.
	"""

class IQSolution(interface.Interface):

	weight = schema.Float( title="The relative correctness of this solution, from 0 to 1",
						   description="""If a question has multiple possible solutions, some may
						   be more right than others. This is captured by the weight field. If there is only
						   one right answer, then it has a weight of 1.0.
						   """,
						   min=0.0,
						   max=1.0,
						   default=1.0 )

	def grade( response ):
		"""
		Determine the correctness of the given response.
		:param response: An :class:`IResponse` object representing the student's input for this
			part of the question.
		:return: Either a boolean value or a number between 0 and 1 indicating how correct
			the student's response was. Typically only True and False will be returned.
		"""

class IQMathSolution(IQSolution):
	"""
	A solution in the math domain.
	"""

class IQNumericMathSolution(IQMathSolution):
	"""
	A solution whose correct answer is numeric in nature, and
	should be graded according to numeric equivalence.
	"""

	value = schema.Float( title="The correct numeric answer; really an arbitrary number" )

class IQSymbolicMathSolution(IQMathSolution):
	"""
	A solution whose correct answer should be interpreted symbolically.
	For example, "twelve pi" or "the square root of two".
	"""


class IQLatexSymbolicMathSolution(IQSymbolicMathSolution):
	"""
	A solution whose correct answer should be interpreted
	as symbols, parsed from latex.
	"""

	value = schema.TextLine( title="The LaTeX form of the correct answer." )

class IQMultipleChoiceSolution(IQSolution):
	"""
	A solution whose correct answer is drawn from a fixed list
	of possibilities. The student is expected to choose from
	the options presented. These will typically be used in isolation as a single part.
	"""
	choices = schema.List( title="The choice strings to present to the user.",
						  value_type=schema.TextLine( title="A rendered value" ) ) # TODO: Again with the IContentFragment?


class IQFreeResponseSolution(IQSolution):
	"""
	A solution whose correct answer is simple text.
	"""

	value = schema.Text( title="The correct text response" )


class IQMatchingSolution(IQSolution):
	"""
	A solution whose answer is a mapping from options in one column (called `labels` for simplicity)
	to options in another column (called `values`). The two lists must have the same
	length.
	"""

	labels = schema.List( title="The list of labels",
						  value_type=schema.TextLine( title="A label-column value" ) )
	values = schema.List( title="The list of labels",
						  value_type=schema.TextLine( title="A value-column value" ) )


class IQuestion(interface.Interface):
	"""
	A question consists of one or more parts (typically one) that require answers.
	It may have prefacing text. It may have other metadata, such as what
	concepts it relates to (e.g., Common Core Standards numbers); such concepts
	will be domain specific.
	"""

	content = schema.Text( title="The content to present to the user, if any." )
	parts = schema.List( title="The ordered parts of the question.",
						 value_type=schema.Object( IQPart, title="A question part" ) )

class IQuestionSet(interface.Interface):
	"""
	An ordered group of related questions generally intended to be
	completed as a unit (aka, a Quiz or worksheet).
	"""

	questions = schema.List( title="The ordered questions in the set.",
							 value_type=schema.Object( IQuestion, title="The questions" ) )

class IResponse(interface.Interface):
	"""
	A response submitted by the student.
	"""

class ITextResponse(IResponse):
	"""
	A response submitted as text.
	"""

	value = schema.Text( title="The response text" )

class IDictResponse(IResponse):
	"""
	A response submitted as a mapping between kes and values.
	"""
	value = schema.Dict( title="The response dictionary",
						 key_type=schema.TextLine( title="The key" ),
						 value_type=schema.TextLine(title="The value") )

IQMathSolution.setTaggedValue( 'response_type', ITextResponse )
IQMatchingSolution.setTaggedValue( 'response_type', IDictResponse )
