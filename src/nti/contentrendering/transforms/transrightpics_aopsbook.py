import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides( interfaces.IDocumentTransformer )


def transform( document ):
    # In aopsbook, rightpic often appear before their containing element( exer, revprob, chall, challhard ), 
    # they need to move down a level into their respective containers. 

    for rightpic in document.getElementsByTagName( 'rightpic' ):
        # Move the rightpic from right before a solution to inside of the solution.
        if rightpic.parentNode.parentNode.nodeName == 'section' and rightpic.parentNode.nextSibling.firstChild.nodeName == 'solution':
            rightpicContainer = rightpic.parentNode
            logger.info("Moving right pic, %s, into solution %s", rightpic, rightpicContainer.nextSibling.firstChild)
            # add rightpic to new parent
            rightpicContainer.nextSibling.firstChild.insert(0, rightpic)
            # remove rightpic from original parent
            rightpicContainer.removeChild(rightpic)

        # Move rightpics down into the approriate exer, exerhard, revprob, chall, or challhard node.
        elif rightpic.parentNode.parentNode.nodeName in ['exer', 'exerhard', 'revprob', 'chall', 'challhard']:
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
