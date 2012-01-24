import unittest
from nti.contentrendering.microdata import items, PROPERTIES_KEY

from hamcrest import assert_that, has_length, has_entry, has_key

class TestMicrodata(unittest.TestCase):

	def test_href(self):
		html = """
			<html>
			<body>
			<div itemscope itemref="taro" itemid="">
			</div>
			<div id="taro">
			   <span itemprop="name">Taro</span>
			   <div itemprop="age">18</div>
			   <div itemprop="friend" itemscope itemref="jiro">
			      ref
			   </div>
			</div>
			<div id="jiro">
			   <div itemprop="name">Jiro</div>
			   <div itemprop="friend" itemscope itemref="saburo">
			      ref
			   </div>
			</div>
			<div id="saburo">
			   <div itemprop="name">Saburo</div>
			   <div itemprop="friend" itemscope itemref="shiro">
			      no ref
			   </div>
			</div>
			</body>
			</html>"""
		
		ls = items(html)
		assert_that(ls, has_length(1))
		d = ls[0]
		
		assert_that(d, has_length(2))
		assert_that(d, has_entry('id',''))
		assert_that(d, has_key(PROPERTIES_KEY))
		
		d = d[PROPERTIES_KEY]
		assert_that(d, has_length(3))
		assert_that(d, has_entry('age',['18']))
		assert_that(d, has_entry('name',['Taro']))
		assert_that(d, has_entry('friend', has_length(1)))
		
		d = d['friend'][0]
		assert_that(d, has_key(PROPERTIES_KEY))
		d = d[PROPERTIES_KEY]
		assert_that(d, has_entry('name',['Jiro']))
		assert_that(d, has_entry('friend', has_length(1)))
		
		d = d['friend'][0]
		assert_that(d, has_key(PROPERTIES_KEY))
		d = d[PROPERTIES_KEY]
		assert_that(d, has_entry('name',['Saburo']))
		assert_that(d, has_entry('friend', has_length(1)))
		
		d = d['friend'][0]
		assert_that(d, has_entry(PROPERTIES_KEY, has_length(0)))

	def test_simple(self):
		html = """<div itemscope>
					<p itemprop="a">1</p>
					<p itemprop="a">2</p>
					<p itemprop="b">test</p>
				 </div>
			   """
		ls = items(html)
		assert_that(ls, has_length(1))
		
		d = ls[0]
		assert_that(d, has_entry(PROPERTIES_KEY, has_length(2)))
		d = d[PROPERTIES_KEY]
		assert_that(d, has_entry('a', ['1','2']))
		assert_that(d, has_entry('b', ['test']))
		
	def test_double(self):
		html = """
				<div itemscope>
 					<span itemprop="favorite-color favorite-fruit">orange</span>
				</div>
			   """
				
		ls = items(html)
		assert_that(ls, has_length(1))
		d = ls[0]
		assert_that(d, has_entry(PROPERTIES_KEY, has_length(2)))
		
		d = d[PROPERTIES_KEY]
		assert_that(d, has_entry('favorite-color', ['orange']))
		assert_that(d, has_entry('favorite-fruit', ['orange']))
		
	def test_type(self):
		html = 	"""
				<section itemscope itemtype="http://example.org/animals#cat">
 					<h1 itemprop="name">Hedral</h1>
 					<p itemprop="desc">Hedral is a male american domestic
 					shorthair, with a fluffy black fur with white paws and belly.</p>
 					<img itemprop="img" src="hedral.jpeg" alt="" title="Hedral, age 18 months"/>
				</section>
				"""
				
		ls = items(html)
		assert_that(ls, has_length(1))
		
		d = ls[0]
		assert_that(d, has_entry('type', 'http://example.org/animals#cat'))
		assert_that(d, has_entry(PROPERTIES_KEY, has_length(3)))
		
		d = d[PROPERTIES_KEY]
		assert_that(d, has_entry('name', ['Hedral']))
		assert_that(d, has_entry('img', ['hedral.jpeg']))
		assert_that(d, has_entry('desc', has_length(1)))
		
	def test_meta(self):
		html=	"""
				<div itemscope itemtype="http://schema.org/Book">
					<div itemprop="reviews" itemscope itemtype="http://schema.org/Review">
						<span itemprop="reviewRating">4</span> stars -
						<b>"<span itemprop="name">A good read.</span>" </b>
						by <span itemprop="author">Bob Smith</span>,
						Written on <meta itemprop="datePublished" content="2006-06-15">June 15, 2006
						<span itemprop="reviewBody">Catcher in the Rye is a fun book. It's a good book to read.</span>
					</div>
					<div itemprop="reviews" itemscope itemtype="http://schema.org/Review">
  						<span itemprop="reviewRating">5</span> stars -
 						<b>"<span itemprop="name">A masterpiece of literature</span>" </b>
						by <span itemprop="author">John Doe</span>,
						Written on <meta itemprop="datePublished" content="2006-05-04">May 4, 2006
						<span itemprop="reviewBody">I really enjoyed this book. It captures the essential
						challenge people face as they try make sense of their lives and grow to adulthood.</span>
					</div>
				</div>
				"""
	
		ls = items(html)
		assert_that(ls, has_length(1))
		
		d = ls[0]
		assert_that(d, has_key(PROPERTIES_KEY))
		assert_that(d, has_entry('type', 'http://schema.org/Book'))

		d = d[PROPERTIES_KEY]
		assert_that(d, has_entry('author', ['Bob Smith', 'John Doe']))
		assert_that(d, has_entry('datePublished', ['2006-06-15', '2006-05-04']))
		assert_that(d, has_entry('name', ['A good read.', 'A masterpiece of literature']))
		assert_that(d, has_entry('reviewBody', has_length(2)))
		assert_that(d, has_entry('reviewRating', ['4', '5']))
		assert_that(d, has_entry('reviews', has_length(2)))
		
		for d in d['reviews']:
			self.assert_(isinstance(d, dict))
			assert_that(d, has_key(PROPERTIES_KEY))
			assert_that(d, has_entry('type', 'http://schema.org/Review'))
			
			p = d[PROPERTIES_KEY]
			assert_that(p, has_key('author'))
			assert_that(p, has_key('name'))
			assert_that(p, has_key('datePublished'))
			assert_that(p, has_key('reviewBody'))
			assert_that(p, has_key('reviewRating'))
			
if __name__ == '__main__':
	unittest.main()
	