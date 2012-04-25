import math

class Hist(object):
	"""
	Simple histograms of float values.
	"""

	# pass None for lo and hi and it will automatically adjust to the min
	# and max values seen.
	# Note:  nbuckets can be passed for backward compatibility.  The
	# display() method can be passed a different nbuckets value.
	def __init__(self, nbuckets=200, lo=0.0, hi=100.0, percentiles= (5, 25, 75, 95)):
		self.data = []  # the raw data points
		self.lo, self.hi = lo, hi
		self.nbuckets = nbuckets
		self.stats_uptodate = False
		self.buckets = [0] * nbuckets
		self.percentiles = percentiles

	# add a value to the collection.
	def add(self, x):
		self.data.append(x)
		self.stats_uptodate = False

	# compute, and set as instance attrs:
	#     n         # of data points
	# the rest are set iff n>0:
	#	min		smallest value in collection
	#	max		largest value in collection
	#	median	midpoint
	#	mean
	#	pct		list of (percentile, score) pairs
	#	var		variance
	#	sdev	population standard deviation (sqrt(variance))
	# self.data is also sorted.
	def compute_stats(self):
		if self.stats_uptodate:
			return
		self.stats_uptodate = True
		data = self.data
		n = self.n = len(data)
		if n == 0:
			return
		data.sort()
		self.min = data[0]
		self.max = data[-1]
		if n & 1:
			self.median = data[n // 2]
		else:
			self.median = (data[n // 2] + data[(n-1) // 2]) / 2.0
			
		# compute mean.
		# add in increasing order of magnitude, to minimize roundoff error.
		if data[0] < 0.0:
			temp = [(abs(x), x) for x in data]
			temp.sort()
			data = [x[1] for x in temp]
			del temp
		
		mean = self.mean = sum(data) / n
		
		# compute variance.
		var = 0.0
		for x in data:
			d = x - mean
			var += d*d
		self.var = var / n
		self.sdev = math.sqrt(self.var)
		
		# compute percentiles.
		self.pct = pct = []
		for p in self.percentiles:
			assert 0.0 <= p <= 100.0
			# in going from data index 0 to index n-1, we move n-1 times.
			# p% of that is (n-1)*p/100.
			i = (n-1)*p/1e2
			if i < 0:
				# just return the smallest.
				score = data[0]
			else:
				whole = int(i)
				frac = i - whole
				score = data[whole]
				if whole < n-1 and frac:
					# move frac of the way from this score to the next.
					score += frac * (data[whole + 1] - score)
				pct.append((p, score))

	# merge other into self.
	def __iadd__(self, other):
		self.data.extend(other.data)
		self.stats_uptodate = False
		return self

	def get_lo_hi(self):
		self.compute_stats()
		lo, hi = self.lo, self.hi
		if lo is None:
			lo = self.min
		if hi is None:
			hi = self.max
		return lo, hi

	def get_bucketwidth(self):
		lo, hi = self.get_lo_hi()
		span = float(hi - lo)
		return span / self.nbuckets

	# set instance var nbuckets to the # of buckets, and buckets to a list
	# of nbuckets counts.
	def fill_buckets(self, nbuckets=None):
		nbuckets = self.nbuckets if nbuckets is None else nbuckets
		if nbuckets <= 0:
			raise ValueError("nbuckets %g > 0 required" % nbuckets)
		self.nbuckets = nbuckets
		self.buckets = buckets = [0] * nbuckets

		# Compute bucket counts.
		lo, _ = self.get_lo_hi()
		bucketwidth = self.get_bucketwidth()
		for x in self.data:
			i = int((x - lo) / bucketwidth)
			if i >= nbuckets:
				i = nbuckets - 1
			elif i < 0:
				i = 0
			buckets[i] += 1
			
		return nbuckets

	# print a histogram to stdout.
	# also sets instance var nbuckets to the # of buckets, and
	# buckts to a list of nbuckets counts, but only if at least one
	# data point is in the collection.
	def display(self, nbuckets=None, WIDTH=61):
		nbuckets = self.nbuckets if nbuckets is None else nbuckets
		if nbuckets <= 0:
			raise ValueError("nbuckets %g > 0 required" % nbuckets)
		self.compute_stats()
		n = self.n
		if n == 0:
			return
		print "%d items; mean %.2f; sdev %.2f" % (n, self.mean, self.sdev)
		print "-> <stat> min %g; median %g; max %g" % (self.min, self.median, self.max)
		
		pcts = ['%g%% %g' % x for x in self.pct]
		print "-> <stat> percentiles:", '; '.join(pcts)

		lo, hi = self.get_lo_hi()
		if lo > hi:
			return

		# hunit is how many items a * represents.  A * is printed for
		# each hunit items, plus any non-zero fraction thereof.
		self.fill_buckets(nbuckets)
		biggest = max(self.buckets)
		hunit, r = divmod(biggest, WIDTH)
		if r:
			hunit += 1
		print "* =", hunit, "items"
		
		# we need ndigits decimal digits to display the largest bucket count.
		ndigits = len(str(biggest))

		# displaying the bucket boundaries is more troublesome.
		bucketwidth = self.get_bucketwidth()
		whole_digits = max(len(str(int(lo))), len(str(int(hi - bucketwidth))))

		frac_digits = 0
		while bucketwidth < 1.0:
			# incrementing by bucketwidth may not change the last displayed
			# digit, so display one more.
			frac_digits += 1
			bucketwidth *= 10.0
			
		s = ("%" + str(whole_digits + 1 + frac_digits) + '.' + str(frac_digits) +
			 'f %' + str(ndigits) + "d")

		bucketwidth = self.get_bucketwidth()
		for i in range(nbuckets):
			n = self.buckets[i]
			print s % (lo + i * bucketwidth, n),
			print '*' * ((n + hunit - 1) // hunit)
