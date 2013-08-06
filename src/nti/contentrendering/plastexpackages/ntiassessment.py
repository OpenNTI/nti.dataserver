#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
A macro package to support the writing of assessments inline with
the rest of content.

These are rendered into HTML as ``<object>`` tags with an NTIID
that matches an object to resolve from the dataserver. The HTML inside the object may or may
not be usable for basic viewing; client applications will use the Question object
from the dataserver to guide the ultimate rendering.

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
			   \naqsolution[weight]<unit1, unit2> A possible solution. The weight, defaulting to one,
				   	is how "correct" this solution is. Some parts may have more compact
					representations of solutions.

					The units are only valid on math parts. If given, it may be an empty list  to specify
					that units are forbidden, or a list of optional units that may be included as part of the
					answer.
			\end{naqsolutions}
			\begin{naqhints}
				\naqhint Arbitrary content giving a hint for how to arrive at the correct
					solution.
			\end{naqhints}
			\begin{naqsolexplanation}
				Arbitrary content explaining how the correct solution is arrived at.
			\end{naqsolexplanation}
		\end{naqsymmathpart}
	\end{naquestion}


$Id$
"""
# All of these have too many public methods
#pylint: disable=R0904
# "not callable" for the default values of None
#pylint: disable=E1102
# access to protected members -> _asm_local_content defined in this module
#pylint: disable=W0212
# "Method __delitem__ is abstract in Node and not overridden"
#pylint: disable=W0223

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import itertools

from zope import schema
from zope.cachedescriptors.property import readproperty

from plasTeX import Base
from plasTeX.Base import Crossref

from nti.assessment import interfaces as as_interfaces, parts, question

from nti.contentfragments import interfaces as cfg_interfaces

from nti.contentrendering import plastexids
from nti.contentrendering.plastexpackages.ntilatexmacros import ntiincludevideo
from nti.contentrendering.plastexpackages._util import LocalContentMixin as _BaseLocalContentMixin

class _LocalContentMixin(_BaseLocalContentMixin):
	# SAJ: HACK. Something about naqvideo and _LocalContentMixin? ALl the parts
	# and solutions from this module are excluded from rendering
	_asm_ignorable_renderables = ()

# Handle custom counter names
class naquestionsetname(Base.Command):
	unicode = ''

class naquestionname(Base.Command):
	unicode = ''

class naqsolutionnumname(Base.Command):
	unicode = ''

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
_LocalContentMixin._asm_ignorable_renderables += (naqsolutions,)

class naqsolution(Base.List.item):

	args = '[weight:float] <units>'
	# We use <> for the units list because () looks like a geometric
	# point, and there are valid answers like that.
	# We also do NOT use the :list conversion, because if the units list
	# has something like an (escaped) % in it, plasTeX fails to tokenize the list
	# Instead, we work with the TexFragment object ourself

	def invoke( self, tex ):
		# TODO: Why is this being done? Does the counter matter?
		self.counter = naqsolutions.counters[0]
		self.position = self.ownerDocument.context.counters[self.counter].value + 1
		#ignore the list implementation
		return Base.Command.invoke(self,tex)

	def units_to_text_list(self):
		"""Find the units, if any, and return a list of their text values"""
		units = self.attributes.get( 'units' )
		if units:
			# Remove trailing delimiter and surrounding whitespace. For consecutive
			# text parts, we have to split ourself
			result = []
			for x in units:
				# We could get elements (Macro/Command) or strings (plastex.dom.Text)
				if getattr( x, 'tagName', None ) == 'math':
					raise ValueError( "Math cannot be roundtripped in units. Try unicode symbols" )
				x = unicode(x).rstrip( ',' ).strip()
				result.extend( x.split( ',' ) )
			return result

	def units_to_html(self):
		units = self.units_to_text_list()
		if units:
			return ','.join( units )
_LocalContentMixin._asm_ignorable_renderables += (naqsolution,)
class naqsolexplanation(_LocalContentMixin, Base.Environment):
	pass
_LocalContentMixin._asm_ignorable_renderables += (naqsolexplanation,)
class _AbstractNAQPart(_LocalContentMixin,Base.Environment):

	# Defines the type of part this maps too
	part_interface = None
	# Defines the type of solution this part produces.
	# Solution objects will be created by adapting the text content of the solution DOM nodes
	# into this interface.
	soln_interface = None
	part_factory = None
	hint_interface = as_interfaces.IQHTMLHint

	def _asm_solutions(self):
		solutions = []
		solution_els = self.getElementsByTagName( 'naqsolution' )
		for solution_el in solution_els:
			#  If the textContent is taken instead of the source of the child element, the
			#  code fails on Latex solutions like $\frac{1}{2}$
			# TODO: Should this be rendered? In some cases yes, in some cases no?
			content = ' '.join([c.source.strip() for c in solution_el.childNodes]).strip()
			if len(content) >= 2 and content.startswith( '$' ) and content.endswith( '$' ):
				content = content[1:-1]

			# Note that this is already a latex content fragment, we don't need
			# to adapt it with the interfaces. If we do, a content string like "75\%" becomes
			# "75\\\\%\\", which is clearly wrong
			solution = self.soln_interface( cfg_interfaces.LatexContentFragment( unicode(content).strip() ) )
			weight = solution_el.attributes['weight']
			if weight is not None:
				solution.weight = weight

			if self.soln_interface.isOrExtends( as_interfaces.IQMathSolution ):
				# Units given? We currently always make units optional, given or not
				# This can easily be changed or configured
				allowed_units = solution_el.units_to_text_list()
				if not allowed_units:
					allowed_units = ('',)
				if '' not in allowed_units:
					allowed_units = list(allowed_units)
					allowed_units.append( '' )
				solution.allowed_units = allowed_units
			solutions.append( solution )

		return solutions

	def _asm_explanation(self):
		exp_els = self.getElementsByTagName( 'naqsolexplanation' )
		assert len(exp_els) <= 1
		if exp_els:
			return exp_els[0]._asm_local_content
		return cfg_interfaces.ILatexContentFragment( '' )

	def _asm_hints(self):
		hints = []
		hint_els = self.getElementsByTagName( 'naqhint' )
		for hint_el in hint_els:
			hint = self.hint_interface( hint_el._asm_local_content )
			hints.append( hint )

		return hints

	def _asm_object_kwargs(self):
		return {}

	def assessment_object( self ):
		# Be careful to turn textContent into plain unicode objects, not
		# plastex Text subclasses, which are also expensive nodes.
		result = self.part_factory( content=self._asm_local_content,
									solutions=self._asm_solutions(),
									explanation=self._asm_explanation(),
									hints=self._asm_hints(),
									**self._asm_object_kwargs()	)

		errors = schema.getValidationErrors( self.part_interface, result )
		if errors: # pragma: no cover
			__traceback_info__ = self.part_interface, errors, result
			raise errors[0][1]
		return result

	def _after_render( self, rendered ):
		super(_AbstractNAQPart,self)._after_render( rendered )
		# The hints and explanations don't normally get rendered
		# by the templates, so make sure they do
		for x in itertools.chain( self.getElementsByTagName( 'naqsolexplanation' ),
								  self.getElementsByTagName( 'naqsolution' ),
								  self.getElementsByTagName( 'naqhint' ),
								  self.getElementsByTagName( 'naqchoice' ),
								  self.getElementsByTagName( 'naqmlabel' ),
								  self.getElementsByTagName( 'naqmvalue' ) ):
			unicode(x)

_LocalContentMixin._asm_ignorable_renderables += (_AbstractNAQPart,)
class naqnumericmathpart(_AbstractNAQPart):
	"""
	Solutions are treated as numbers for the purposes of grading.
	"""

	part_interface = as_interfaces.IQNumericMathPart
	part_factory = parts.QNumericMathPart
	soln_interface = as_interfaces.IQNumericMathSolution

class naqsymmathpart(_AbstractNAQPart):
	"""
	Solutions are treated symbolicaly for the purposes of grading.
	"""

	part_interface = as_interfaces.IQSymbolicMathPart
	part_factory = parts.QSymbolicMathPart
	soln_interface = as_interfaces.IQLatexSymbolicMathSolution


class naqfreeresponsepart(_AbstractNAQPart):
	part_interface = as_interfaces.IQFreeResponsePart
	part_factory = parts.QFreeResponsePart
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
	part_factory = parts.QMultipleChoicePart
	soln_interface = as_interfaces.IQMultipleChoiceSolution

	#forcePars = True

	def _asm_choices(self):
		return [x._asm_local_content for x in self.getElementsByTagName( 'naqchoice' )]

	def _asm_object_kwargs(self):
		return { 'choices': self._asm_choices() }

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

class naqmultiplechoicemultipleanswerpart(_AbstractNAQPart):
	"""
	A multiple-choice / multiple-answer part (usually used as the sole part to a question).
	It must have a child listing the possible choices; the solutions are collapsed
	into this child; at least one of them must have a weight equal to 1::.  Further the all
	solutions with a weight of 1:: are required to be submitted to receive credit for the
	question

		\begin{naquestion}
			Arbitrary prefix content goes here.
			\begin{naqmultiplechoicemultipleanswerpart}
			        Arbitrary content for this part goes here.
				\begin{naqchoices}
			   		\naqchoice Arbitrary content for the choices.
					\naqchoice[1] This is one part of a right choice.
					\naqchoice[1] This is another part of a right choice.
	                        \end{naqchoices}
				\begin{naqsolexplanation}
					Arbitrary content explaining how the correct solution is arrived at.
				\end{naqsolexplanation}
			\end{naqmultiplechoicemultipleanswerpart}
		\end{naquestion}
	"""

	part_interface = as_interfaces.IQMultipleChoiceMultipleAnswerPart
	part_factory = parts.QMultipleChoiceMultipleAnswerPart
	soln_interface = as_interfaces.IQMultipleChoiceMultipleAnswerSolution

	def _asm_choices(self):
		return [x._asm_local_content for x in self.getElementsByTagName( 'naqchoice' )]

	def _asm_object_kwargs(self):
		return { 'choices': self._asm_choices() }

	def _asm_solutions(self):
		solutions = []
		# By definition, there can only be one solution element.
		solution_el = self.getElementsByTagName( 'naqsolution' )[0]

		solution = self.soln_interface( solution_el.answer )
		weight = solution_el.attributes['weight']
		if weight is not None:
			solution.weight = weight
		solutions.append( solution )

		return solutions

	def digest( self, tokens ):
		res = super(naqmultiplechoicemultipleanswerpart,self).digest( tokens )
		# Validate the document structure: we have a naqchoices child
		# with at least two of its own children, and at least one
		# weight == 1.  There is no explicit solution
		_naqchoices = self.getElementsByTagName( 'naqchoices' )
		assert len(_naqchoices) == 1
		_naqchoices = _naqchoices[0]
		assert len(_naqchoices) > 1, "Must have more than one choice"
		assert any( (_naqchoice.attributes['weight'] == 1.0 for _naqchoice in _naqchoices) )
		assert len(self.getElementsByTagName( 'naqsolutions' )) == 0

		# Tranform the implicit solutions into a list of 0-based
		# indices.
		_naqsolns = self.ownerDocument.createElement( 'naqsolutions' )
		_naqsolns.macroMode = _naqsolns.MODE_BEGIN
		_naqsoln = self.ownerDocument.createElement( 'naqsolution' )
		_naqsoln.attributes['weight'] = 1.0
		_naqsoln.argSource = '[1.0]'
		_naqsoln.answer = []
		for i, _naqchoice in enumerate(_naqchoices):
			if _naqchoice.attributes['weight'] and _naqchoice.attributes['weight'] == 1:
				_naqsoln.answer.append( i )
		_naqsolns.appendChild( _naqsoln )
		self.insertAfter( _naqsolns, _naqchoices )
		return res

class naqmatchingpart(_AbstractNAQPart):
	"""
	A matching part (usually used as the sole part to a question).
	It must have two children, one listing the possible labels, with the
	correct solution's index in brackets, and the other listing the possible
	values::

		\begin{naquestion}
			Arbitrary prefix content goes here.
			\begin{naqmatchingpart}
			   Arbitrary content for this part goes here.
			   \begin{naqmlabels}
			   		\naqmlabel[2] What is three times two?
					\naqmlabel[0] What is four times three?
					\naqmlabel[1] What is five times two thousand?
				\end{naqmlabels}
				\begin{naqmvalues}
					\naqmvalue Twelve
					\naqmvalue Ten thousand
					\naqmvalue Six
				\end{naqmvalues}
				\begin{naqsolexplanation}
					Arbitrary content explaining how the correct solution is arrived at.
				\end{naqsolexplanation}
			\end{naqmatchingpart}
		\end{naquestion}
	"""

	part_interface = as_interfaces.IQMatchingPart
	part_factory = parts.QMatchingPart
	soln_interface = as_interfaces.IQMatchingSolution

	#forcePars = True

	def _asm_labels(self):
		return [x._asm_local_content for x in self.getElementsByTagName( 'naqmlabel' )]

	def _asm_values(self):
		return [x._asm_local_content for x in self.getElementsByTagName( 'naqmvalue' )]

	def _asm_object_kwargs(self):
		return { 'labels': self._asm_labels(),
				 'values': self._asm_values() }

	def _asm_solutions(self):
		solutions = []
		solution_els = self.getElementsByTagName( 'naqsolution' )
		for solution_el in solution_els:
			solution = self.soln_interface( solution_el.answer )
			weight = solution_el.attributes['weight']
			if weight is not None:
				solution.weight = weight
			solutions.append( solution )

		return solutions

	def digest( self, tokens ):
		res = super(naqmatchingpart,self).digest( tokens )
		# Validate the document structure: we have a naqlabels child with
		# at least two of its own children, an naqvalues child of equal length
		# and a proper matching between the two
		if self.macroMode != Base.Environment.MODE_END:
			_naqmlabels = self.getElementsByTagName( 'naqmlabels' )
			assert len(_naqmlabels) == 1
			_naqmlabels = _naqmlabels[0]
			assert len(_naqmlabels) > 1, "Must have more than one label; instead got: " + str([x for x in _naqmlabels])
			_naqmvalues = self.getElementsByTagName( 'naqmvalues' )
			assert len(_naqmvalues) == 1
			_naqmvalues = _naqmvalues[0]
			assert len(_naqmvalues) == len(_naqmlabels), "Must have exactly one value per label"

			for i in range(len(_naqmlabels)):
				assert any( (_naqmlabel.attributes['answer'] == i for _naqmlabel in _naqmlabels) )
			assert len(self.getElementsByTagName( 'naqsolutions' )) == 0

			# Tranform the implicit solutions into an array
			_naqsolns = self.ownerDocument.createElement( 'naqsolutions' )
			_naqsolns.macroMode = _naqsolns.MODE_BEGIN
			answer = {}
			for i, _naqmlabel in enumerate(_naqmlabels):
				answer[i] = _naqmlabel.attributes['answer']
			_naqsoln = self.ownerDocument.createElement( 'naqsolution' )
			_naqsoln.attributes['weight'] = 1.0
			# Also put the attribute into the argument source, for presentation
			_naqsoln.argSource = '[%s]' % _naqsoln.attributes['weight']
			_naqsoln.answer = answer
			_naqsolns.appendChild( _naqsoln )
			self.insertAfter( _naqsolns, _naqmvalues)
		return res

class naqchoices(Base.List):
	pass

class naqmlabels(Base.List):
	pass

class naqmvalues(Base.List):
	pass

class naqvalue(_LocalContentMixin,Base.List.item):
	@readproperty
	def _asm_local_content(self):
		return cfg_interfaces.ILatexContentFragment(unicode(self.textContent).strip())

class naqchoice(naqvalue):
	args = "[weight:float]"

class naqmlabel(naqvalue):
	args = "[answer:int]"

class naqmvalue(naqvalue):
	pass

class naqhints(Base.List):
	pass

class naqhint(_LocalContentMixin,Base.List.item):

	def _after_render( self, rendered ):
		self._asm_local_content = rendered

_LocalContentMixin._asm_ignorable_renderables += (naqchoices, naqmlabels, naqmvalues, naqvalue, naqchoice, naqmlabel, naqmvalue, naqhints, naqhint)

class naqvideo(ntiincludevideo):
	blockType = True

class naquestion(_LocalContentMixin,Base.Environment,plastexids.NTIIDMixin):
	args = '[individual:str]'
	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'naquestion'
	blockType = True
	_ntiid_cache_map_name = '_naquestion_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'naq.'
	_ntiid_title_attr_name = 'ref' # Use our counter to generate IDs if no ID is given
	_ntiid_type = as_interfaces.NTIID_TYPE

	def invoke( self, tex ):
		_t = super(naquestion,self).invoke(tex)
		if 'individual' in self.attributes and self.attributes['individual'] == 'individual=true':
			self.attributes['individual'] = 'true'
		return _t

	@property
	def _ntiid_get_local_part(self):
		result = self.attributes.get( 'probnum' ) or self.attributes.get( "questionnum" )
		if not result:
			result = super(naquestion,self)._ntiid_get_local_part
		return result

	def _asm_videos(self):
		videos = []
		# video_els = self.getElementsByTagName( 'naqvideo' )
		# for video_el in video_els:
		#	videos.append( video_el._asm_local_content )

		return ''.join(videos)

	def _asm_question_parts(self):
		return [x.assessment_object() for x in self if hasattr(x,'assessment_object')]

	def assessment_object(self):
		result = question.QQuestion( content=self._asm_local_content,
					     parts=self._asm_question_parts())
		errors = schema.getValidationErrors( as_interfaces.IQuestion, result )
		if errors: # pragma: no cover
			raise errors[0][1]
		result.ntiid = self.ntiid # copy the id
		return result

class naquestionref(Crossref.ref):
	pass

from persistent.list import PersistentList
class naquestionset(Base.List, plastexids.NTIIDMixin):

	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'naquestionset'
	_ntiid_cache_map_name = '_naquestionset_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'naq.set.'
	_ntiid_title_attr_name = 'ref' # Use our counter to generate IDs if no ID is given
	_ntiid_type = as_interfaces.NTIID_TYPE

	mimeType = "application/vnd.nextthought.naquestionset"

	def assessment_object(self):
		questions = [qref.idref['label'].assessment_object() for qref in self.getElementsByTagName( 'naquestionref' )]
		questions = PersistentList( questions )
		result = question.QQuestionSet( questions )
		errors = schema.getValidationErrors( as_interfaces.IQuestionSet, result )
		if errors: # pragma: no cover
			raise errors[0][1]
		result.ntiid = self.ntiid # copy the id
		return result

def ProcessOptions( options, document ):

	document.context.newcounter( 'naqsolutionnum' )
	document.context.newcounter( 'naquestion' )
	document.context.newcounter( 'naquestionset' )
