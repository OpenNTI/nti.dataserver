from plasTeX import Base, Node
from nti.contentrendering import domutils
from plasTeX.Base.LaTeX import Math
import plasTeX

import logging
logger = logging.getLogger(__name__)

from zope import interface
from . import interfaces
interface.moduleProvides(interfaces.IDocumentTransformer)


class ntixymatrix(Base.Command):
	@property
	def source(self):
		return self._source

class ntixydisplaymath(Math.displaymath):
	resourceTypes = ['png', 'svg']

class ntixymath(Math.math):
	resourceTypes = ['png', 'svg']

def transform(document):
	document.context['ntixymatrix'] = ntixymatrix
	document.context['ntixymath'] = ntixymath
	document.context['ntixydisplaymath'] = ntixydisplaymath

	xys = domutils.findNodesStartsWith(document, 'xymatrix')

	logger.info( 'Will transform on %s', xys )

	for xy in xys:
		fixxy(document, xy)

def fixxy(document, xy):
	#figure out if the xy would be the only child
	parent = xy.parentNode

	xynodes = []
	source = xy.source.strip()

	nextSibling = xy

	while(nextSibling.nodeName != 'bgroup'):

		xynodes.append(nextSibling)

		nextSibling = nextSibling.nextSibling

	xynodes.append(nextSibling)


	source = ''.join([node.source.strip() for node in xynodes])

	newxy = document.createElement('ntixymatrix')
	newxy._source = source
	parent.replaceChild(newxy, xynodes[0])

	for oldNode in xynodes[1:]:
		parent.removeChild(oldNode)

	if getattr(parent, 'mathMode', False):
		onlyxy = True

		for child in parent.childNodes:

			if child == newxy:
				continue

			if child.nodeType == Node.TEXT_NODE:
				if child.textContent.strip():
					onlyxy = False
					break

			if child.nodeType == Node.ELEMENT_NODE:
				onlyxy = False
				break

		if onlyxy:
			newparent = None
			if parent.nodeName == 'math':
				newparent = document.createElement('ntixymath')
			else:
				newparent = document.createElement('ntixydisplaymath')

			if newparent != None:
				try:
					parent.parentNode.replaceChild(newparent, parent)
				except plasTeX.DOM.NotFoundErr:
					#Since its not where its suppossed to be, hopefully its in an attribute
					vals = parent.parentNode.attributes.values()

					for val in vals:
						if getattr(val, 'childNodes', None):
							for child in val.childNodes:
								if child == parent:
									val.replaceChild(newparent, parent)

				newparent.appendChild(newxy)




