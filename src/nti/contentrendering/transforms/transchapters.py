import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides(interfaces.IDocumentTransformer)


def transform(document):
	# Chapterauthor and chapterquote need to move down a level, inside
	# their respective chapters.
	for chapterquote in document.getElementsByTagName( 'chapterquote'):
		chapterauthor = chapterquote.parentNode.getElementsByTagName( 'chapterauthor' )[0]
		parent = chapterquote.parentNode
		# move it up out of containing par and raggedbottom, etc
		while parent:
			if parent.nextSibling and parent.nextSibling.nodeName == 'chapter':
				break
			parent = parent.parentNode

		if parent and parent.nextSibling:
			logger.info( "Moving chaterquote/author (%s/%s) to %s", chapterquote, chapterauthor, parent )
			chapterquote.parentNode.removeChild( chapterauthor )
			chapterquote.parentNode.removeChild( chapterquote )
			parent.nextSibling.insert( 0, chapterquote )
			parent.nextSibling.insert( 1, chapterauthor )
