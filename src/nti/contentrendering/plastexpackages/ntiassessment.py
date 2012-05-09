#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A macro package to support the writing of assessments inline with
the rest of content.

At the moment, this ships with template package to render these
assessments as HTML elements, but that's not part of the long-term plan.

Example::

	\begin{naquestion}[individual=true]
		Arbitrary content goes here.
		\begin{naqsymmathpart}
		Arbitrary content goes here.
		\begin{naqsolutions}
			\naqsolution Some solution
		\end{naqsolutions}
		\end{naqsymmathpart}
	\end{naquestion}


"""
# All of these have too many public methods
#pylint: disable=R0904

from __future__ import print_function, unicode_literals

from plasTeX import Base

class naqsolutions(Base.List):

	counters = ['naqsolutionnum']
	args = '[ init:int ]'

	def invoke( self, tex ):
		res = super(naqsolutions, self).invoke( tex )

		if 'init' in self.attributes and self.attributes['init']:
			self.ownerDocument.context.counters[self.counters[0]].setcounter( self.attributes['init'] )
		elif self.macroMode != Base.Environment.MODE_END:
			self.ownerDocument.context.counters[self.counters[0]].setcounter(0)

		return res

	def digest( self, tokens ):
		#After digesting loop back over the children moving nodes before
		#the first item into the first item
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
	#Ordinary list items can accept a value
	#args = ''

	def invoke( self, tex ):
		self.counter = naqsolutions.counters[0]
		self.position = self.ownerDocument.context.counters[self.counter].value + 1
		#ignore the list implementation
		return Base.Command.invoke(self,tex)

class naqsymmathpart(Base.Environment):
	pass
class naqfreeresponsepart(Base.Environment):
	pass

class naquestion(Base.Environment):
	args = '[individual:str]'

def ProcessOptions( options, document ):

	document.context.newcounter( 'naqsolutionnum' )
