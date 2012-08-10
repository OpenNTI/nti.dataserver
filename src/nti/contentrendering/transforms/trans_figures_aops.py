import logging
logger = logging.getLogger( __name__ )

from zope import interface
from . import interfaces
interface.moduleProvides( interfaces.IDocumentTransformer )


def transform( document ):
    # In aopsbook, rightpic, leftpic, and parpic elements often appear before their containing element( exer, revprob,
    # chall, challhard ), and they need to moved into their respective containers. 

    nodeTypes = [ 'rightpic', 'leftpic', 'parpic' ]
    problemElements = [ 'chall', 'challhard', 'exer', 'exerhard', 'revprob', 'part', 'parthard' ]

    for nodeType in nodeTypes:
        for node in document.getElementsByTagName( nodeType ):
            parentNode = node.parentNode

            # Move the *pic node from right before a solution to inside of the solution.
            if parentNode.parentNode.nodeName == 'section' and \
                    parentNode.nextSibling.firstChild.nodeName == 'solution':
                logger.info("Moving %s, %s, into solution %s", nodeType, node, parentNode.nextSibling.firstChild)
                parentNode.nextSibling.firstChild.insert( 0, node )
                parentNode.removeChild( node )

            # Handle cases where the *pic node is in a separate par element before the first node of a set.
            elif len(parentNode.childNodes) == 1 and parentNode.parentNode.firstChild == parentNode and \
                    parentNode.nextSibling.nodeName in problemElements:
                logger.info("Moving %s, %s, into the first node, %s , in the set of %s", nodeType, node, 
                             parentNode.nextSibling, parentNode.nextSibling.nodeName)
                parentNode.nextSibling.insert( 0, node )
                parentNode.removeChild( node )

            # Move *pics down into the approriate container node.
            elif parentNode.parentNode.nodeName in problemElements:
                nodeContainer = parentNode.parentNode
                parentType = parentNode.parentNode.nodeName

                lastChildNode = nodeContainer.lastChild
                while lastChildNode.firstChild.nodeName == 'hint':
                    lastChildNode = lastChildNode.previousChild

                #make sure that it's indeed the *pic that we should move
                if lastChildNode.lastChild == node and nodeContainer.nextSibling != None and \
                        nodeContainer.nextSibling.nodeName in problemElements:
                    #move it to the parent's next sibling
                    logger.debug( "Moving %s %s of %s %s to its parent's next sibling, %s %s", nodeType, node, 
                                 parentType, nodeContainer, parentType, nodeContainer.nextSibling )
                    lastChildNode.removeChild( node )
                    nodeContainer.nextSibling.insert( 0, node )

            # Remove empty parents
            if parentNode.childNodes == []:
                logger.debug( "Removing the empty former %s parent node.", nodeType )
                _t = parentNode.parentNode
                _t.removeChild( parentNode )
