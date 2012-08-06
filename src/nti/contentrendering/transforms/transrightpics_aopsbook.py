import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides( interfaces.IDocumentTransformer )


def transform( document ):
    # In aopsbook, rightpic often appear before their containing element( exer, revprob, chall, challhard ), 
    # they need to move down a level into their respective containers. 

    problemElements = ['chall', 'challhard', 'exer', 'exerhard', 'revprob', 'part', 'parthard']

    for rightpic in document.getElementsByTagName( 'rightpic' ):
        parentNode = rightpic.parentNode

        if rightpic.nextSibling and rightpic.nextSibling.source.strip() == '':
            logger.debug("Removing empty sibling.")
            parentNode.removeChild(rightpic.nextSibling)

        # Move the rightpic from right before a solution to inside of the solution.
        if rightpic.parentNode.parentNode.nodeName == 'section' and \
                rightpic.parentNode.nextSibling.firstChild.nodeName == 'solution':
            rightpicContainer = rightpic.parentNode
            logger.info("Moving right pic, %s, into solution %s", rightpic, rightpicContainer.nextSibling.firstChild)
            # add rightpic to new parent
            rightpicContainer.nextSibling.firstChild.insert(0, rightpic)
            # remove rightpic from original parent
            rightpicContainer.removeChild(rightpic)

        # Handle cases where the rightpic is in a separate par element before the first node of a set.
        elif len(parentNode.childNodes) == 1 and parentNode.parentNode.firstChild == parentNode and \
                parentNode.nextSibling.nodeName in problemElements:
            logger.debug("Moving rightpic, %s, into the first node, %s , in the set of %s", rightpic, parentNode.nextSibling, parentNode.nextSibling.nodeName)
            parentNode.parentNode.childNodes[1].childNodes[0].insert( 0, rightpic )
            parentNode.removeChild( rightpic )

        # Handle cases where the rightpic is before the first node of a set, but has been grouped as a separate
        # par element inside the first node.  This case moves the leftpic into the main body of the node.
        elif len(parentNode.childNodes) == 1 and parentNode.parentNode.firstChild == parentNode and \
                parentNode.parentNode.nodeName in problemElements:
            logger.debug("Moving rightpic, %s, into the main body of node, %s , in the set of %s", rightpic, parentNode.parentNode, parentNode.parentNode.nodeName)
            parentNode.parentNode.childNodes[1].insert( 0, rightpic )
            parentNode.removeChild( rightpic )

        # Move rightpics down into the approriate exer, exerhard, revprob, chall, or challhard node.
        elif parentNode.parentNode.nodeName in problemElements:
            rightpicContainer = rightpic.parentNode.parentNode
            parentType = rightpic.parentNode.parentNode.nodeName

            lastChildNode = rightpicContainer.lastChild
            while lastChildNode.firstChild.nodeName == 'hint':
                lastChildNode = lastChildNode.previousChild

            #make sure that it's indeed the rightpic that we should move
            if lastChildNode.lastChild == rightpic  and rightpicContainer.nextSibling is not None and rightpicContainer.nextSibling.nodeName in problemElements:
                #move it to the parent's next sibling
                logger.info( "Moving rightpic %s of %s %s to its parent's next sibling, %s %s", rightpic, parentType, rightpicContainer, parentType, rightpicContainer.nextSibling )
                #step 1: rm
                lastChildNode.removeChild( rightpic )
                #step2: add it to the next sibling as the first child
                rightpicContainer.nextSibling.firstChild.insert( 0, rightpic )

        # If the rightpic is the only element of a par node merge it with the parent's next sibling, if it exists,
        # to prevent the creation of <p></p> elements.
        elif len(parentNode.childNodes) == 1 and parentNode.nextSibling is not None:
            logger.debug("Merging rightpic %s into it's parent nodes next sibling %s.", rightpic, parentNode.nextSibling)
            parentNode.nextSibling.insert( 0, rightpic )
            parentNode.removeChild( rightpic )

        # Remove empty parents
        if parentNode.childNodes == []:
            logger.debug("Removing the empty former rightpic parent node.")
            _t = parentNode.parentNode
            _t.removeChild(parentNode)
