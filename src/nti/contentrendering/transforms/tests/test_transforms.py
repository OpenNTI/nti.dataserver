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

	
	
