import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides( interfaces.IDocumentTransformer )


def transform( document ):
    # In aopsbook, rightpic often appear before their containing element( exer, revprob, chall, challhard ), 
    # they need to move down a level into their respective containers. 

    for rightpic in document.getElementsByTagName( 'rightpic' ):
        parentNode = rightpic.parentNode

        if rightpic.nextSibling and rightpic.nextSibling.source.strip() == '':
            logger.debug("Removing empty sibling.")
            rightpic.parentNode.removeChild(rightpic.nextSibling)

        # Move the rightpic from right before a solution to inside of the solution.
        if rightpic.parentNode.parentNode.nodeName == 'section' and rightpic.parentNode.nextSibling.firstChild.nodeName == 'solution':
            rightpicContainer = rightpic.parentNode
            logger.info("Moving right pic, %s, into solution %s", rightpic, rightpicContainer.nextSibling.firstChild)
            # add rightpic to new parent
            rightpicContainer.nextSibling.firstChild.insert(0, rightpic)
            # remove rightpic from original parent
            rightpicContainer.removeChild(rightpic)

        # Handle cases where the rightpic is before the first node of a set.
        elif len(parentNode.childNodes) == 1 and parentNode.parentNode.firstChild == parentNode:
            parentNode.parentNode.childNodes[1].insert( 0, rightpic )
            parentNode.removeChild( rightpic )

        # Move rightpics down into the approriate exer, exerhard, revprob, chall, or challhard node.
        elif rightpic.parentNode.parentNode.nodeName in ['chall', 'challhard', 'exer', 'exerhard', 'revprob', 'part', 'parthard']:
            rightpicContainer = rightpic.parentNode.parentNode
            parentType = rightpic.parentNode.parentNode.nodeName

            lastChildNode = rightpicContainer.lastChild
            while lastChildNode.firstChild.nodeName == 'hint':
                lastChildNode = lastChildNode.previousChild

            #make sure that it's indeed the rightpic that we should move
            if _isChild(lastChildNode, rightpic ) and len(rightpicContainer.childNodes) > 1 and rightpicContainer.nextSibling != None and rightpicContainer.nextSibling.nodeName in ['chall', 'challhard', 'exer', 'exerhard', 'revprob', 'part', 'parthard']:
                #move it to the parent's next sibling
                logger.info( "Moving rightpic %s of %s %s to its parent's next sibling, %s %s", rightpic, parentType, rightpicContainer, parentType, rightpicContainer.nextSibling )
                #step 1: rm
                lastChildNode.removeChild( rightpic )
                #step2: add it to the next sibling as the first child
                rightpicContainer.nextSibling.firstChild.insert( 0, rightpic )

        # Remove empty parents
        if parentNode.childNodes == []:
            logger.debug("Removing the empty former rightpic parent node.")
            _t = parentNode.parentNode
            _t.removeChild(parentNode)

def _isChild(parentNode, potentialChild):
    if parentNode is None:
        return False
    for child in parentNode.childNodes:
        if child == potentialChild:
            return True
    return False
