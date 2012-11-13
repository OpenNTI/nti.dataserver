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
			   \naqsolution[weight] A possible solution. The weight, defaulting to one,
				   	is how "correct" this solution is. Some parts may have more compact
					representations of solutions.
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

from __future__ import print_function, unicode_literals

from zope import interface
from zope import component
from zope import schema
from zope.cachedescriptors.property import readproperty

import os
import itertools
import simplejson as json # Needed for sort_keys, ensure_ascii
import codecs

from nti.contentrendering.plastexpackages import interfaces

import nti.externalization.internalization
from nti.externalization.externalization import toExternalObject
from nti.assessment import interfaces as as_interfaces, parts, question
from nti.contentrendering import plastexids, interfaces as cdr_interfaces
from nti.contentfragments import interfaces as cfg_interfaces

from plasTeX import Base
from plasTeX.Base import Crossref
from plasTeX.Renderers import render_children

def _asm_local_textcontent(self):
	"""
	Collects the text content for nodes that are direct
	children of `self`, *not* recursively. Returns a `unicode` object,
	*not* a :class:`plasTeX.DOM.Text` object.
	"""
	output = []
	for item in self.childNodes:
		if item.nodeType == self.TEXT_NODE:
			output.append(unicode(item))
		elif getattr(item, 'unicode', None) is not None:
			output.append(item.unicode)
	return cfg_interfaces.ILatexContentFragment( ''.join( output ).strip() )

def _asm_rendered_textcontent(self):
	"""
	Collects the rendered values of the children of self. Can only be used
	while in the rendering process. Returns a `unicode` object.
	"""
	childNodes = []
	for item in self.childNodes:
		# Skipping the parts and solutions that come from this module except naqvideo.
		# SAJ: This is a temporary hack until naqvideo works properly as a _LocalContentMixin.
		if type(item).__module__ == __name__ and not isinstance(item, naqvideo):
			continue
		childNodes.append( item )

	output = render_children( self.renderer, childNodes )
	return cfg_interfaces.HTMLContentFragment( ''.join( output ).strip() )

class _LocalContentMixin(object):
	"""
	Something that can collect local content. Defines one property,
	`_asm_local_content` to be the value of the local content. If this object
	has never been through the rendering pipline, this will be a LaTeX fragment
	(probably with missing information and mostly useful for debuging).
	If this object has been rendered, then it will be an HTML content fragment
	according to the templates.

	Mixin order matters, this needs to be first.
	"""

	_asm_local_content = readproperty(_asm_local_textcontent)
	def _after_render( self, rendered ):
		self._asm_local_content = _asm_rendered_textcontent( self )

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


class naqsolution(Base.List.item):

	args = '[weight:float]'

	def invoke( self, tex ):
		# TODO: Why is this being done? Does the counter matter?
		self.counter = naqsolutions.counters[0]
		self.position = self.ownerDocument.context.counters[self.counter].value + 1
		#ignore the list implementation
		return Base.Command.invoke(self,tex)


class naqsolexplanation(_LocalContentMixin, Base.Environment):
	pass

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

class naqvideo(Base.Command):
	args = 'videourl thumbnail'
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
		video_els = self.getElementsByTagName( 'naqvideo' )
		#for video_el in video_els:
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
class naquestionset(Base.List,plastexids.NTIIDMixin):

	# Only classes with counters can be labeled, and \label sets the
	# id property, which in turn is used as part of the NTIID (when no NTIID is set explicitly)
	counter = 'naquestionset'
	_ntiid_cache_map_name = '_naquestionset_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'naq.set.'
	_ntiid_title_attr_name = 'ref' # Use our counter to generate IDs if no ID is given
	_ntiid_type = as_interfaces.NTIID_TYPE


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

@interface.implementer(interfaces.IAssessmentExtractor)
@component.adapter(cdr_interfaces.IRenderedBook)
class _AssessmentExtractor(object):
	"""
	"Transforms" a rendered book by extracting assessment information into a separate file
	called ``assessment_index.json.`` This file describes a dictionary with the following
	structure::

		Items => { # Keyed by NTIID of the file
			NTIID => string # This level is about an NTIID section
			filename => string # The relative containing file for this NTIID
			AssessmentItems => { # Keyed by NTIID of the question
				NTIID => string # The NTIID of the question
				... # All the rest of the keys of the question object
			}
			Items => { # Keyed by NTIIDs of child sections; recurses
				# As containing, except 'filename' will be null/None
			}
		}

	"""

	def __init__( self, book=None ):
		# Usable as either a utility factory or an adapter
		pass

	def transform( self, book ):
		index = {'Items': {}}
		self._build_index( book.document.getElementsByTagName( 'document' )[0], index['Items'] )
		#index['filename'] = index.get( 'filename', 'index.html' ) # This leads to duplicate data
		index['href'] = index.get( 'href', 'index.html' )
		with codecs.open( os.path.join( book.contentLocation, 'assessment_index.json'), 'w', encoding='utf-8' ) as fp:
			json.dump( index, fp, indent='\t', sort_keys=True, ensure_ascii=True ) # sort_keys for repeatability. Do force ensure_ascii because even though we're using codes to encode automatically, the reader might not decode
		return index

	def _build_index( self, element, index ):
		"""
		Recurse through the element adding assessment objects to the index,
		keyed off of NTIIDs.

		:param dict index: The containing index node. Typically, this will be
			an ``Items`` dictionary in a containing index.
		"""
		ntiid = getattr( element, 'ntiid', None )
		if not ntiid:
			# If we hit something without an ntiid, it's not a section-level
			# element, it's a paragraph or something like it. Thus we collapse into
			# the parent. Obviously, we'll only look for AssessmentObjects inside of here
			element_index = index
		else:
			assert ntiid not in index, "NTIIDs must be unique"
			element_index = index[ntiid] = {}

			element_index['NTIID'] = ntiid
			element_index['filename'] = getattr( element, 'filename', None )
			if not element_index['filename'] and getattr( element, 'filenameoverride', None ):
				# FIXME: XXX: We are assuming the filename extension. Why aren't we finding
				# these at filename? See EclipseHelp.zpts for comparison
				element_index['filename'] = getattr( element, 'filenameoverride' ) + '.html'
			element_index['href'] = getattr( element, 'url', element_index['filename'] )

		assessment_objects = element_index.setdefault( 'AssessmentItems', {} )

		for child in element.childNodes:
			ass_obj = getattr( child, 'assessment_object', None )
			if callable( ass_obj ):
				int_obj = ass_obj()
				self._ensure_roundtrips( int_obj, provenance=child ) # Verify that we can round-trip this object
				assessment_objects[child.ntiid] = toExternalObject( int_obj )
			else: # assessment_objects are leafs, never have children to worry about
				if getattr( child, 'ntiid', None ):
					containing_index = element_index.setdefault( 'Items', {} ) # we have a child with an NTIID; make sure we have a container for it
				else:
					containing_index = element_index # an unnamed thing; wrap it up with us; should only have AssessmentItems
				self._build_index( child, containing_index )

	def _ensure_roundtrips( self, assm_obj, provenance=None ):
		ext_obj = toExternalObject( assm_obj ) # No need to go into its children, like parts.
		__traceback_info__ = provenance, assm_obj, ext_obj
		raw_int_obj = type(assm_obj)() # Use the class of the object returned as a factory.
		nti.externalization.internalization.update_from_external_object( raw_int_obj, ext_obj, require_updater=True )
		factory = nti.externalization.internalization.find_factory_for( toExternalObject( assm_obj ) ) # Also be sure factories can be found
		assert factory is not None
		# The ext_obj was mutated by the internalization process, so we need to externalize
		# again. Or run a deep copy (?)
