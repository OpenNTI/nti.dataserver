import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides(interfaces.IDocumentTransformer)


def transform(document):
	# Chapterauthor and chapterquote need to move down a level, inside
	# their respective chapters.
	for chapterquote in document.getElementsByTagName( 'chapterquote'):
		if len(chapterquote.parentNode.getElementsByTagName( 'chapterauthor' )):
			chapterauthor = chapterquote.parentNode.getElementsByTagName( 'chapterauthor' )[0]
			parent = chapterquote.parentNode
		else:
			chapterauthor = chapterquote.parentNode.parentNode.getElementsByTagName( 'chapterauthor' )[0]
			parent = chapterquote.parentNode.parentNode
		# move it up out of containing par and raggedbottom, etc
		while parent:
			if parent.nextSibling and parent.nextSibling.nodeName == 'chapter':
				break
			parent = parent.parentNode

		if parent and parent.nextSibling:
			logger.info( "Moving chaterquote/author (%s/%s) to %s", chapterquote, chapterauthor, parent )
			chapterauthor.parentNode.removeChild( chapterauthor )
			chapterquote.parentNode.removeChild( chapterquote )
			parent.nextSibling.insert( 0, chapterquote )
			parent.nextSibling.insert( 1, chapterauthor )
			
	for rightpic in document.getElementsByTagName( 'rightpic' ):
		if rightpic.parentNode.parentNode.nodeName == 'exer':
			exerParent = rightpic.parentNode.parentNode
			
			#make sure that it's indeed the rightpic that we should move
			if exerParent.lastChild.firstChild == rightpic and exerParent.nextSibling != None and exerParent.nextSibling.nodeName == 'exer':
				#move it down a level
				logger.info( "Moving rightpic %s of exercise %s down a level to exercise %s", rightpic, exerParent, exerParent.nextSibling )
				#step 1: rm
				exerParent.lastChild.removeChild(rightpic)
				#step2: add it to the next sibling
				exerParent.nextSibling.firstChild.appendChild(rightpic)
	
