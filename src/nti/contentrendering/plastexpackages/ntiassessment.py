#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
A macro package to support the writing of assessments inline with
the rest of content.

At the moment, this ships with template package to render these
assessments as HTML elements, but that's not part of the long-term plan.

Example::

	\begin{naquestion}[individual=true]
		Arbitrary prefix content goes here. This may be rendered to the document.

		Questions consist of sequential parts, often just one part. The parts
		do not have to be homogeneous.
		\begin{naqsymmathpart}
		   Arbitrary content for this part goes here. This may be rendered to the document.

		   A part has one or more possible solutions. The solutions are of the same type,
		   determined implicitly by the part type.
		   \begin{naqsolutions}
			   \naqsolution[weight] A possible solution. The weight, defaulting to one, is how "correct" this solution is.
			\end{naqsolutions}
			\begin{naqsolexplanation}
			Arbitrary content explaining how the correct solution is arrived at.
			\end{naqsolexplanation}
		\end{naqsymmathpart}
	\end{naquestion}


$Id$
"""
# All of these have too many public methods
#pylint: disable=R0904

from __future__ import print_function, unicode_literals

from nti.assessment import interfaces as as_interfaces
from nti.contentrendering import plastexids
from plasTeX import Base

class naqsolutions(Base.List):

	counters = ['naqsolutionnum']
	args = '[ init:int ]'

	def invoke( self, tex ):
		# TODO: Why is this being done?
		res = super(naqsolutions, self).invoke( tex )

		if 'init' in self.attributes and self.attributes['init']:
			self.ownerDocument.context.counters[self.counters[0]].setcounter( self.attributes['init'] )
		elif self.macroMode != Base.Environment.MODE_END:
			self.ownerDocument.context.counters[self.counters[0]].setcounter(0)

		return res

	def digest( self, tokens ):
		#After digesting loop back over the children moving nodes before
		#the first item into the first item
		# TODO: Why is this being done?
		res = super(naqsolutions, self).digest(tokens)
		if self.macroMode != Base.Environment.MODE_END:
			nodesToMove = []

			for node in self:

				if isinstance(node, Base.List.item):
					nodesToMove.reverse()
					for nodeToMove in nodesToMove:
						self.removeChild(nodeToMove)
						node.insert(0, nodeToMove)
					break

				nodesToMove.append(node)

		return res


class naqsolution(Base.List.item):

	args = '[weight:float]'

	def invoke( self, tex ):
		# TODO: Why is this being done? Does the counter matter?
		self.counter = naqsolutions.counters[0]
		self.position = self.ownerDocument.context.counters[self.counter].value + 1
		#ignore the list implementation
		return Base.Command.invoke(self,tex)

class naqsolexplanation(Base.Environment):
	pass

class _AbstractNAQPart(Base.Environment):

	# Defines the type of part this maps too
	part_interface = None
	# Defines the type of solution this part produces.
	# Solution objects will be created by adapting the text content of the solution DOM nodes
	# into this interface.
	soln_interface = None
	part_factory = None

class naqnumericmathpart(_AbstractNAQPart):
	"""
	Solutions are treated as numbers for the purposes of grading.
	"""

	part_interface = as_interfaces.IQNumericMathPart
	soln_interface = as_interfaces.IQNumericMathSolution

class naqsymmathpart(_AbstractNAQPart):
	"""
	Solutions are treated symbolicaly for the purposes of grading.
	"""

	part_interface = as_interfaces.IQSymbolicMathPart
	soln_interface = as_interfaces.IQLatexSymbolicMathSolution

class naqfreeresponsepart(_AbstractNAQPart):
	part_interface = as_interfaces.IQFreeResponsePart
	soln_interface = as_interfaces.IQFreeResponseSolution


class naqmultiplechoicepart(_AbstractNAQPart):
	"""
	A multiple-choice part (usually used as the sole part to a question).
	It must have a child listing the possible choices; the solutions are collapsed
	into this child; at least one of them must have a weight equal to 1::

		\begin{naquestion}
			Arbitrary prefix content goes here.
			\begin{naqmultiplechoicepart}
			   Arbitrary content for this part goes here.
			   \begin{naqchoices}
			   		\naqchoice Arbitrary content for the choice.
					\naqchoice[1] Arbitrary content for this choice; this is the right choice.
					\naqchoice[0.5] This choice is half correct.
				\end{naqchoices}
				\begin{naqsolexplanation}
					Arbitrary content explaining how the correct solution is arrived at.
				\end{naqsolexplanation}
			\end{naqmultiplechoicepart}
		\end{naquestion}
	"""

	part_interface = as_interfaces.IQMultipleChoicePart
	soln_interface = as_interfaces.IQMultipleChoiceSolution

	#forcePars = True

	def digest( self, tokens ):
		res = super(naqmultiplechoicepart,self).digest( tokens )
		# Validate the document structure: we have a naqchoices child with
		# at least two of its own children, and at least one weight == 1. There is no explicit solution
		_naqchoices = self.getElementsByTagName( 'naqchoices' )
		assert len(_naqchoices) == 1
		_naqchoices = _naqchoices[0]
		assert len(_naqchoices) > 1, "Must have more than one choice"
		assert any( (_naqchoice.attributes['weight'] == 1.0 for _naqchoice in _naqchoices) )
		assert len(self.getElementsByTagName( 'naqsolutions' )) == 0

		# Tranform the implicit solutions into explicit 0-based solutions
		_naqsolns = self.ownerDocument.createElement( 'naqsolutions' )
		_naqsolns.macroMode = _naqsolns.MODE_BEGIN
		for i, _naqchoice in enumerate(_naqchoices):
			if _naqchoice.attributes['weight']:
				_naqsoln = self.ownerDocument.createElement( 'naqsolution' )
				_naqsoln.attributes['weight'] = _naqchoice.attributes['weight']
				# Also put the attribute into the argument source, for presentation
				_naqsoln.argSource = '[%s]' % _naqsoln.attributes['weight']
				_naqsoln.appendChild( self.ownerDocument.createTextNode( str(i) ) )
				_naqsolns.appendChild( _naqsoln )
		self.insertAfter( _naqsolns, _naqchoices )
		return res

class naqchoices(Base.List):
	pass

class naqchoice(Base.List.item):
	args = "[weight:float]"

class naquestion(Base.Environment,plastexids.NTIIDMixin):
	args = '[individual:str]'
	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'naquestion'
	_ntiid_cache_map_name = '_naquestion_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'naq.'
	_ntiid_title_attr_name = 'ref' # Use our counter to generate IDs if no ID is given

	@property
	def _ntiid_get_local_part(self):
		result = self.attributes.get( 'probnum' ) or self.attributes.get( "questionnum" )
		if not result:
			result = super(naquestion,self)._ntiid_get_local_part
		return result

def ProcessOptions( options, document ):

	document.context.newcounter( 'naqsolutionnum' )
	document.context.newcounter( 'naquestion' )
