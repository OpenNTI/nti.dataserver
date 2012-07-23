from . import ConfiguringTestBase
from .. import performTransforms

from nti.contentrendering.transforms.transchapters import transform as _domTransform

from hamcrest import assert_that, has_length, greater_than_or_equal_to, is_
import anyjson as json

import plasTeX
from plasTeX.TeX import TeX


from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText

class EmptyMockDocument(object):

	childNodes = ()

	def __init__(self):
		self.context = {}

	def getElementsByTagName(self, name): return ()

class TestTransforms(ConfiguringTestBase):

	def test_transforms(self):
		res = performTransforms(EmptyMockDocument())
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )

def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.aopsbook}',),
                                    bodies=maths )
		
def test_rightpicTransform():
	example = br"""
	\exercises 
	
	\exer One side of an isosceles triangle is three times as long as another side
	of the triangle.  If the perimeter of the triangle is 140, then what is the length of the 
	base of the triangle?
	
	\rightpic{geometry_135.pdf}
	\exer
	Squares are constructed on each of the sides of a triangle  as shown to the right.  If the perimeter of the triangle is 17, then what is the perimeter of the nine-sided figure that is 
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	
#	import pdb 
#	pdb.set_trace()
	
	exers = dom.getElementsByTagName('exer')
	assert_that( exers, has_length(2))
	assert_that( exers[0].lastChild.firstChild.nodeName, is_( 'rightpic' ) )
	#run the transform
	_domTransform( dom )
	
	assert_that( exers[1].firstChild.lastChild.nodeName, is_( 'rightpic' ) )
	
def test_startRightPicTransform():
	example = br"""
	\exercises 

	\rightpic{geometry_134.pdf}
	\exer If each square in the diagram at the right has side length 1, then
	what is the perimeter of the figure traced in bold?
	
	\exer
	Squares are constructed on each of the sides of a triangle  as shown to the right.  If the perimeter of the triangle is 17, then what is the perimeter of the nine-sided figure that is 
	"""
	
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	exers = dom.getElementsByTagName('exer')
	#before
	assert_that( exers[0].firstChild.firstChild.nodeName, is_( 'rightpic' ) )
	
	#run the transform
	_domTransform( dom )
	exers = dom.getElementsByTagName('exer')
	
	#after: We expect the image to stay right where it was. no movement.
	assert_that( exers[0].firstChild.firstChild.nodeName, is_( 'rightpic' ) )

def test_revProbRightPicTransform():
	example = br"""
	\reviewprobs
	
	\revprob
	Square tiles 9~inches on a side exactly cover the floor of a rectangular room.  The border tiles are white and all other tiles are blue.  The room measures 18~feet by 15~feet.  How many tiles are white?
	\MOEMS % Set 14 2E
	
	
	\rightpic{geometry_136.pdf}
	\revprob
	If adjacent sides meet at right angles in the figure at the right, what is the number of centimeters in the perimeter of the figure? \MathCounts
	"""	
	
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	
	_domTransform( dom )
	#We expect the rightpic to have been moved down a level and belong to the last review problem as opposed to the first one.
	revProbWithPic = dom.getElementsByTagName( 'revprob')[1];
	assert_that( revProbWithPic.firstChild.lastChild.nodeName, is_( 'rightpic' )) 
	
def test_challProbRightPicTransform():
	example = br"""
	\challengeprobs

	
	\chall In rectangle $ABCD$, point $X$ is the midpoint of $\seg{AD}$ and $Y$ is the midpoint
	of $\seg{CD}$.  What fraction of the area of the rectangle is enclosed
	by $\tri AXY$?
	
	\chall Point $T$ is on side $\seg{QR}$ of $\tri PQR$.  Find the ratio $QT/QR$ if the area of $\tri PQT$ 
	is 75  and the area of $\tri PTR$ is 40. \hints~\hint{geom2:basesoftriangles}
	
	
	
	\rightpic{geometry_179.pdf}
	\chall\label{prob:wxyzandtri}
	In the diagram on the right, $WXYZ$ is a rectangle. The area of triangle $ZXA$ is 36, and $ZA=3AY$. 
	
	\begin{parts}
	\part If $XY = 12$, then what is the area of rectangle $WXYZ$?
	\part If $XY = 9$, then what is the area of rectangle $WXYZ$?
	\part If $XY = 6$, then what is the area of rectangle $WXYZ$?
	\part Do you notice a pattern in your answers to the first three parts?
	Will this pattern hold for other values of $XY$?
	\end{parts}
	


	"""
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	
	import pdb
	pdb.set_trace()
	_domTransform( dom )
	#We expect the rightpic to have been moved down a level and belong to the last review problem as opposed to the first one.
	revProbWithPic = dom.getElementsByTagName( 'chall')[2];
	assert_that( revProbWithPic.firstChild.lastChild.nodeName, is_( 'rightpic' ))
