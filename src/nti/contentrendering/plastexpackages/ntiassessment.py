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

from zope import interface
from zope import component
from zope import schema

import os

import simplejson as json
import codecs

from . import interfaces

from nti.externalization.externalization import toExternalObject
from nti.assessment import interfaces as as_interfaces, parts, question
from nti.contentrendering import plastexids, interfaces as cdr_interfaces
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

def _asm_local_textcontent(self):
	"""
	Collects the text content for nodes that are direct
	children of `self`, *not* recursively. Returns a `unicode` object,
	*not* a :class:`plasTeX.DOM.Text` object.
	"""
	output = []
	for item in self.childNodes:
		if item.nodeType == self.TEXT_NODE:
			output.append(item)
		elif getattr(item, 'unicode', None) is not None:
			output.append(item.unicode)
	return ''.join( output ).strip()

class _AbstractNAQPart(Base.Environment):

	# Defines the type of part this maps too
	part_interface = None
	# Defines the type of solution this part produces.
	# Solution objects will be created by adapting the text content of the solution DOM nodes
	# into this interface.
	soln_interface = None
	part_factory = None

	def _asm_solutions(self):
		solutions = []
		solution_els = self.getElementsByTagName( 'naqsolution' )
		for solution_el in solution_els:
			solution = self.soln_interface( unicode(solution_el.textContent).strip() )
			weight = solution_el.attributes['weight']
			if weight is not None:
				solution.weight = weight
			solutions.append( solution )

		return solutions

	def _asm_explanation(self):
		exp_els = self.getElementsByTagName( 'naqsolexplanation' )
		assert len(exp_els) <= 1
		if exp_els:
			return unicode(exp_els[0].textContent).strip()

	def _asm_hints(self):
		pass

	_asm_local_textcontent = _asm_local_textcontent

	def _asm_object_kwargs(self):
		return {}

	def assessment_object( self ):
		# Be careful to turn textContent into plain unicode objects, not
		# plastex Text subclasses, which are also expensive nodes.
		result = self.part_factory( content=self._asm_local_textcontent(),
									solutions=self._asm_solutions(),
									explanation=self._asm_explanation(),
									hints=self._asm_hints(),
									**self._asm_object_kwargs()	)

		errors = schema.getValidationErrors( self.part_interface, result )
		if errors: # pragma: no cover
			raise errors[0][1]
		return result

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
		return [unicode(x.textContent).strip() for x in self.getElementsByTagName( 'naqchoice' )]

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
	_ntiid_type = as_interfaces.NTIID_TYPE


	@property
	def _ntiid_get_local_part(self):
		result = self.attributes.get( 'probnum' ) or self.attributes.get( "questionnum" )
		if not result:
			result = super(naquestion,self)._ntiid_get_local_part
		return result

	_asm_local_textcontent = _asm_local_textcontent

	def _asm_question_parts(self):
		return [x.assessment_object() for x in self if hasattr(x,'assessment_object')]

	def assessment_object(self):
		result = question.QQuestion( content=self._asm_local_textcontent(),
									 parts=self._asm_question_parts() )
		errors = schema.getValidationErrors( as_interfaces.IQuestion, result )
		if errors: # pragma: no cover
			raise errors[0][1]
		result.ntiid = self.ntiid # copy the id
		return result

def ProcessOptions( options, document ):

	document.context.newcounter( 'naqsolutionnum' )
	document.context.newcounter( 'naquestion' )

@interface.implementer(interfaces.IAssessmentExtractor)
@component.adapter(cdr_interfaces.IRenderedBook)
class _AssessmentExtractor(object):

	def __init__( self, book=None ):
		# Usable as either a utility factory or an adapter
		pass

	def transform( self, book ):
		index = {}
		self._build_index( book.document.getElementsByTagName( 'document' )[0], index.setdefault( 'Items', {} ) )
		index['filename'] = index.get( 'filename', 'index.html' )
		index['href'] = index.get( 'href', 'index.html' )
		with codecs.open( os.path.join( book.contentLocation, 'assessment_index.json'), 'w', encoding='utf-8' ) as fp:
			json.dump( index, fp, indent='\t' )
		return index

	def _build_index( self, element, index ):
		"""
		Recurse through the element adding assessment objects to the index,
		keyed off of NTIIDs.
		"""
		ntiid = getattr( element, 'ntiid', None )
		if not ntiid:
			# If we hit something without an ntiid, it's not a section-level
			# element, it's a paragraph or something like it. Thus we collapse into
			# the parent
			ntiid_index = index
		else:
			ntiid_index = {}
			index[ntiid] = ntiid_index

			ntiid_index['NTIID'] = ntiid
			ntiid_index['filename'] = getattr( element, 'filename', None )
			if not ntiid_index['filename'] and getattr( element, 'filenameoverride', None ):
				# FIXME: XXX: We are assuming the filename extension. Why aren't we finding
				# these at filename? See EclipseHelp.zpts for comparison
				ntiid_index['filename'] = getattr( element, 'filenameoverride' ) + '.html'
			ntiid_index['href'] = getattr( element, 'url', ntiid_index['filename'] )

		assessment_objects = ntiid_index.setdefault( 'AssessmentItems', {} )

		for child in element.childNodes:
			ass_obj = getattr( child, 'assessment_object', None )
			if callable( ass_obj ):
				assessment_objects[child.ntiid] = toExternalObject( ass_obj())
				# No need to go into its children, like parts.
			else:
				if getattr( child, 'ntiid', None ):
					child_index = ntiid_index.setdefault( 'Items', {} )
				else:
					child_index = ntiid_index
				self._build_index( child, child_index )
