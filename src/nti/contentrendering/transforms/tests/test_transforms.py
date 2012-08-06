from . import ConfiguringTestBase
from .. import performTransforms

from nti.contentrendering.transforms.transrightpics_aopsbook import transform as rightpicTransform

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
	rightpicTransform( dom )

	assert_that( exers[1].firstChild.firstChild.nodeName, is_( 'rightpic' ) )

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
	assert_that( len(exers[0].childNodes), is_( 2 ) )
	assert_that( exers[0].firstChild.firstChild.nodeName, is_( 'rightpic' ) )

	#run the transform
	rightpicTransform( dom )
	exers = dom.getElementsByTagName('exer')

	#after: We expect the image to still be the first child of the first child, but to be merged into
	# the main par element of the exer node.
	assert_that( len(exers[0].childNodes), is_( 1 ) )
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
	rightpicTransform( dom )
	#We expect the rightpic to have been moved down a level and belong to the last review problem as opposed to the first one.

	revProbWithPic = dom.getElementsByTagName( 'revprob')[1];
	assert_that( revProbWithPic.firstChild.firstChild.nodeName, is_( 'rightpic' ))

def test_revProbRightPicTransformNoMove():
	example = br"""
	\reviewprobs

	\revprob
	\rightpic{geometry_136.pdf}
	Square tiles 9~inches on a side exactly cover the floor of a rectangular room.  The border tiles are white and all other tiles are blue.  The room measures 18~feet by 15~feet.  How many tiles are white?
	\MOEMS % Set 14 2E


	\revprob
	If adjacent sides meet at right angles in the figure at the right, what is the number of centimeters in the perimeter of the figure? \MathCounts
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	rightpicTransform( dom )
	#We expect the rightpic to be where it started.

	revProbWithPic = dom.getElementsByTagName( 'revprob')[0]
	assert_that( revProbWithPic.firstChild.firstChild.nodeName, is_( 'rightpic' ))

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
	rightpicTransform( dom )
	#We expect the rightpic to have been moved down a level and belong to the last challenge problem as opposed to the first one.
	revProbWithPic = dom.getElementsByTagName( 'chall')[2];
	assert_that( revProbWithPic.firstChild.firstChild.nodeName, is_( 'rightpic' ))

def test_challRightPicTransformFirstElementOwnPar():
	example = br"""
\challengeprobs


\rightpic{geometry_216.pdf}
\chall In the diagram at the left, $O$ is the center of the circle, $MNOP$ is a
rectangle, and the area of the circle is $100\pi$.  What is the length of
diagonal $\seg{NP}$ of the rectangle?
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	rightpicTransform( dom )
        #We expect the rightpic to have been moved down a level and belong to the last part as opposed to the first one.
	challWithPic = dom.getElementsByTagName( 'chall' )[0]
	assert_that( challWithPic.firstChild.firstChild.nodeName, is_( 'rightpic' ))

def test_solutionRightPicTransform():
	example = br"""

\section{Some section}

\begin{problem}{}%\rightpic{chap2diag.108}}                                                                             
In the figure below, $AOB$ is a straight line.  What is the measure of $\angle AOB$?

\centpic{geometry_29.pdf}\end{problem}



\rightpic{geometry_86.pdf}
\begin{solution}
If we don't see the answer right away, we can try to figure out what portion
of a circle the angle cuts off.  We draw a circle with center $O$ as
in the diagram to the right.  Now we can see that the angle cuts off
half a circle (whichever side of the line we pick).  So,
\[\angle AOB =
\frac{1}{2}(360\dgg) = 180\dgg.\]

This angle's name is easy to remember: a \Def{straight angle}
 is an angle that is really a straight line\index{angle!straight}.
\end{solution}

	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	rightpicTransform( dom )
	#We expect the rightpic to have been moved down into the solution.
	solutionWithPic = dom.getElementsByTagName( 'solution')[0];
	assert_that( solutionWithPic.firstChild.nodeName, is_( 'rightpic' ))

def test_partRightPicTransform():
	example = br"""
\begin{parts}
\part Ravi's triangle is a right triangle, so its area is half the product of its legs.
This means Ravi's triangle has area $(8)(18)/2 = 72$ square feet.

\rightpic{geometry_65.pdf}
\part
We only know how to find the areas of rectangles and right triangles, but Ranu's triangle
is neither of these.  So, we split Ranu's triangle into pieces we can handle.
We draw a segment from the top vertex of Ranu's triangle to the floor such that
this segment is perpendicular to the floor.  This segment has length 8 feet
because the top of the room is 8 feet from the floor.  Ranu's original triangle
is now divided into two right triangles, and we know how to find the
area of right triangles.

\end{parts}
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
	rightpicTransform( dom )
	#We expect the rightpic to have been moved down a level and belong to the last part as opposed to the first one.
	partWithPic = dom.getElementsByTagName( 'part')[1];
	assert_that( partWithPic.firstChild.firstChild.nodeName, is_( 'rightpic' ))

def test_partRightPicTransformNoMove():
	example = br"""
\begin{parts}
\part
\rightpic{geometry_65.pdf}
Ravi's triangle is a right triangle, so its area is half the product of its legs.
This means Ravi's triangle has area $(8)(18)/2 = 72$ square feet.

\part
We only know how to find the areas of rectangles and right triangles, but Ranu's triangle
is neither of these.  So, we split Ranu's triangle into pieces we can handle.
We draw a segment from the top vertex of Ranu's triangle to the floor such that
this segment is perpendicular to the floor.  This segment has length 8 feet
because the top of the room is 8 feet from the floor.  Ranu's original triangle
is now divided into two right triangles, and we know how to find the
area of right triangles.

\end{parts}
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	rightpicTransform( dom )
	#We expect the rightpic to be were it started.
	partWithPic = dom.getElementsByTagName( 'part')[0]
	assert_that( partWithPic.firstChild.firstChild.nodeName, is_( 'rightpic' ))
