from __future__ import print_function, unicode_literals

###########################################################################
# TextIndexNG V 3
# The next generation TextIndex for Zope
#
# This software is governed by a license. See
# LICENSE.txt for the terms of this license.
###########################################################################

"""
ResultList

$Id: resultset.py 2238 2010-04-07 13:00:36Z zagy $
"""

from BTrees.LLBTree import union as union64
from BTrees.LLBTree import difference as difference64
from BTrees.LLBTree import intersection as intersection64

from zopyx.txng3.core.resultset import ResultSet, WordList

from nti.contentsearch.zopyxtxng3coredoclist import DocidList
    
def intersectionResultSets(sets):
    """ perform intersection of ResultSets """
    
    if not sets:
        return ResultSet(DocidList(), WordList())
    
    docids = sets[0].getDocids()
    words = WordList(sets[0].getWords())
    
    for s in sets[1:]:
        docids = intersection64(docids, s.docids)
        words.extend(s.words)
    return ResultSet(docids, words)


def unionResultSets(sets):
    """ perform intersection of ResultSets """
    
    docids = DocidList()
    words = WordList()
    for s in sets:
        docids = union64(docids, s.docids)
        words.extend(s.words)
    return ResultSet(docids, words)

def inverseResultSet(all_docids, s): 
    """ perform difference between all docids and a resultset """    
    docids = difference64(DocidList(all_docids), s.getDocids())
    return ResultSet(docids, set.getWords())
