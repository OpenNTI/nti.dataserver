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
		if rightpic.parentNode.parentNode.nodeName == 'exer' or rightpic.parentNode.parentNode.nodeName == 'revprob' or rightpic.parentNode.parentNode.nodeName == 'chall' or rightpic.parentNode.parentNode.nodeName == 'challhard':
			rightpicContainer = rightpic.parentNode.parentNode
			parentType = rightpic.parentNode.parentNode.nodeName
			
			#make sure that it's indeed the rightpic that we should move
			if rightpicContainer.lastChild.firstChild == rightpic and rightpicContainer.nextSibling != None and rightpicContainer.nextSibling.nodeName == parentType :
				#move it down a level
				logger.info( "Moving rightpic %s of %s %s down a level to %s %s", rightpic, parentType, rightpicContainer, parentType, rightpicContainer.nextSibling )
				#step 1: rm
				rightpicContainer.lastChild.removeChild( rightpic )
				#step2: add it to the next sibling
				rightpicContainer.nextSibling.firstChild.appendChild( rightpic )
	
