import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides( interfaces.IDocumentTransformer )


def transform( document ):
    # In aopsbook, leftpic often appear before their containing element( exer, revprob, chall, challhard ), 
    # they need to move down a level into their respective containers. 

    problemElements = ['chall', 'challhard', 'exer', 'exerhard', 'revprob', 'part', 'parthard']

    for leftpic in document.getElementsByTagName( 'leftpic' ):
        parentNode = leftpic.parentNode

        if leftpic.nextSibling and leftpic.nextSibling.source.strip() == '':
            logger.debug("Removing empty sibling.")
            leftpic.parentNode.removeChild(leftpic.nextSibling)

        # Move the leftpic from right before a solution to inside of the solution.
        if leftpic.parentNode.parentNode.nodeName == 'section' and leftpic.parentNode.nextSibling.firstChild.nodeName == 'solution':
            leftpicContainer = leftpic.parentNode
            logger.info("Moving leftpic, %s, into solution %s", leftpic, leftpicContainer.nextSibling.firstChild)
            # add leftpic to new parent
            leftpicContainer.nextSibling.firstChild.insert(0, leftpic)
            # remove leftpic from original parent
            leftpicContainer.removeChild(leftpic)

        # Handle cases where the leftpic is in a separate par element before the first node of a set.
        elif len(parentNode.childNodes) == 1 and parentNode.parentNode.firstChild == parentNode and \
                parentNode.nextSibling.nodeName in problemElements:
            logger.debug("Moving leftpic, %s, into the first node, %s , in the set of %s", leftpic, parentNode.nextSibling, parentNode.nextSibling.nodeName)
            parentNode.nextSibling.firstChild.insert( 0, leftpic )
            parentNode.removeChild( leftpic )

        # Handle cases where the leftpic is before the first node of a set, but has been grouped as a separate
        # par element inside the first node.  This case moves the leftpic into the main body of the node.
        elif len(parentNode.childNodes) == 1 and parentNode.parentNode.firstChild == parentNode and \
                parentNode.parentNode.nodeName in problemElements:
            logger.debug("Moving leftpic, %s, into the main body of node, %s , in the set of %s", leftpic, parentNode.parentNode, parentNode.parentNode.nodeName)
            parentNode.parentNode.childNodes[1].insert( 0, leftpic )
            parentNode.removeChild( leftpic )

        # Move leftpics down into the approriate exer, exerhard, revprob, chall, or challhard node.
        elif leftpic.parentNode.parentNode.nodeName in problemElements:
            leftpicContainer = leftpic.parentNode.parentNode
            parentType = leftpic.parentNode.parentNode.nodeName

            lastChildNode = leftpicContainer.lastChild
            while lastChildNode.firstChild.nodeName == 'hint':
                lastChildNode = lastChildNode.previousChild

            #make sure that it's indeed the leftpic that we should move
            if lastChildNode.lastChild == leftpic and leftpicContainer.nextSibling != None and \
                    leftpicContainer.nextSibling.nodeName in problemElements:
                #move it to the parent's next sibling
                logger.info( "Moving leftpic %s of %s %s to its parent's next sibling, %s %s", leftpic, parentType, leftpicContainer, parentType, leftpicContainer.nextSibling )
                #step 1: rm
                lastChildNode.removeChild( leftpic )
                #step2: add it to the next sibling as the first child
                leftpicContainer.nextSibling.firstChild.insert( 0, leftpic )

        # If the leftpic is the only element of a par node merge it with the parent's next sibling, if it exists,
        # to prevent the creation of <p></p> elements.
        elif len(parentNode.childNodes) == 1 and parentNode.nextSibling is not None:
            logger.debug("Merging leftpic %s into it's parent nodes next sibling %s.", leftpic, parentNode.nextSibling)
            parentNode.nextSibling.insert( 0, leftpic )
            parentNode.removeChild( leftpic )

        # Remove empty parents
        if parentNode.childNodes == []:
            logger.debug("Removing the empty former leftpic parent node.")
            _t = parentNode.parentNode
            _t.removeChild(parentNode)
