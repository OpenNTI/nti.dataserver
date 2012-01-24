from . import ConfiguringTestBase
from .. import performTransforms

from hamcrest import assert_that, has_length, greater_than_or_equal_to

class EmptyMockDocument(object):

	childNodes = ()

	def __init__(self):
		self.context = {}

	def getElementsByTagName(self, name): return ()

class TestTransforms(ConfiguringTestBase):

	def test_transforms(self):
		res = performTransforms(EmptyMockDocument())
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )
