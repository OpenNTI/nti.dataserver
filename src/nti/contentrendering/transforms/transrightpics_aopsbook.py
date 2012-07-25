import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides( interfaces.IDocumentTransformer )


def transform( document ):
    # In aopsbook, rightpic often appear before their containing element( exer, revprob, chall, challhard ), 
    # they need to move down a level into their respective containers. 

    for rightpic in document.getElementsByTagName( 'rightpic' ):
        if rightpic.parentNode.parentNode.nodeName == 'exer' or rightpic.parentNode.parentNode.nodeName == 'revprob' or rightpic.parentNode.parentNode.nodeName == 'chall' or rightpic.parentNode.parentNode.nodeName == 'challhard':
            rightpicContainer = rightpic.parentNode.parentNode
            parentType = rightpic.parentNode.parentNode.nodeName

            lastChildNode = rightpicContainer.lastChild
            while lastChildNode.firstChild.nodeName == 'hint':
                lastChildNode = lastChildNode.previousChild

            #make sure that it's indeed the rightpic that we should move
            if lastChildNode.firstChild == rightpic and rightpicContainer.nextSibling != None and rightpicContainer.nextSibling.nodeName == parentType :
                #move it down a level
                logger.info( "Moving rightpic %s of %s %s down a level to %s %s", rightpic, parentType, rightpicContainer, parentType, rightpicContainer.nextSibling )
                #step 1: rm
                lastChildNode.removeChild( rightpic )
                #step2: add it to the next sibling as the first child
                rightpicContainer.nextSibling.firstChild.insert( 0, rightpic )




