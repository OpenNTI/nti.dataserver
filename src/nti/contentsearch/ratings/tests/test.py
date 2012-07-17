from scikits.crab.models import MatrixPreferenceDataModel
from scikits.crab.metrics import pearson_correlation
from scikits.crab.similarities import UserSimilarity
from scikits.crab.similarities import ItemSimilarity
from scikits.crab.recommenders.knn import UserBasedRecommender
from scikits.crab.recommenders.knn import ItemBasedRecommender
import scikits.crab.recommenders.svd.classes as svd
import random
import math
from sets import Set

def logistic(sigma):
	return 1.0 / (1.0 + 2.71828 ** sigma)

def pearson(x,y):
	# Pearson correlation coefficient
	if len(x) == 0: return 0
	avx, avy = sum(x) * 1.0 / len(x), sum(y) * 1.0 / len(y)
	varx = sum([(v - avx)**2 for v in x]) * 1.0 / len(x)
	vary = sum([(v - avy)**2 for v in y]) * 1.0 / len(y)
	cov = sum([(u - avx) * (v - avy) for u,v in zip(x,y)]) * 1.0 / len(x)
	pearson = cov / (varx ** 0.5) / (vary ** 0.5)
	return pearson

def create_test_database(users,docs,params,fill):
	"""
	Emulates documents having different extents of various qualities and users
	having different levels of appreciation (possibly negative) for each
	quality. At params=1, for example, this roughly corresponds to "goodness"
	for the documents and "having good taste" for the users. Multiplying
	the user personality matrix by the document quality matrix gives a
	realistic, high-correlation database for testing purposes
	"""
	user_personalities = []
	for i in range(users):
		user_personalities.append([])
		for j in range(params):
			user_personalities[i].append(random.randrange(21) - 10)
	doc_characteristics = []
	for i in range(docs):
		doc_characteristics.append([])
		for j in range(params):
			doc_characteristics[i].append(random.randrange(21) - 10)
	preference_matrix = []
	for i in range(users):
		preference_matrix.append([])
		for j in range(docs):
			tot = 0
			for k in range(params):
				# Future possibility: give personality traits a weight inversely
				# proportional to their index to mirror a power law distribution
				tot += user_personalities[i][k] * doc_characteristics[j][k]
			# Expected absolute value pre-division is (110/21)^2, or 27.43,
			# params ** 0.5 term normalizes for more extreme total sums at higher
			# params values, square root due to the nature of the random walk
			# standard deviation
			preference_matrix[i].append(logistic(tot / 13 / (params ** 0.5)))
	result = {}
	for i in range(users):
		result[str(i)] = {}
		for j in range(docs):
			rng = random.randrange(1000)
			if rng < fill * 1000: result[str(i)][str(j)] = preference_matrix[i][j]
	return preference_matrix, result

class CrabRecommender(object):
	def model(self,data): return MatrixPreferenceDataModel(data)

class SimilarityBasedRecommender(CrabRecommender):
	def create_recommender(self,data):
		model = self.model(data)
		similarity = self.similarity(model)
		return self.recommender(model, similarity, with_preference=True)

class UserRecommender(SimilarityBasedRecommender):
	def __init__(self):
		self.recommender = UserBasedRecommender
	def similarity(self, model):
		return UserSimilarity(model, pearson_correlation)
	def __str__(self): return "User Recommender"

class ItemRecommender(SimilarityBasedRecommender):
	def __init__(self):
		self.recommender = ItemBasedRecommender
	def similarity(self, model):
		return ItemSimilarity(model, pearson_correlation)
	def __str__(self): return "Item Recommender"
		
class MatrixRecommender(CrabRecommender):
	def create_recommender(self,data):
		return svd.MatrixFactorBasedRecommender(self.model(data))
	def __str__(self): return "Matrix Recommender"
	
def test_database(givens, complete, recommender_function, tests=60):
	# Recommender
	recommender = recommender_function(givens)
	x,y = [],[]
	fails = 0
	# Have to go through these gymnastics rather than just picking random
	# indices from complete because at low densities there might be a row 
	# or column that's not in the database at all
	users = givens.keys()
	docs = []
	for u in users:
		for d in givens[u]:
			if d not in docs: docs.append(d)
	for i in range(tests):
		while True:
			test_user = int(users[random.randrange(len(users))])
			test_doc = int(docs[random.randrange(len(docs))])
			if str(test_doc) not in givens[str(test_user)]:
				break
		result = recommender.estimate_preference(str(test_user),str(test_doc))
		correct = complete[test_user][test_doc]
		if math.isnan(result): fails += 1
		else:
			x.append(complete[test_user][test_doc])
			y.append(result)
		#print complete[test_user][test_doc], result
	a = fails*1.0/tests
	b = pearson(x,y)
	return a,b

def run_database_test(users=30, docs=30, params=8, fill=0.5, tests=60, 
		rec=UserRecommender().create_recommender):
	complete, givens = create_test_database(users, docs, params, fill)
	return test_database(givens, complete, rec)

def run_tests():
	num_tries = 5
	trials = []
	# Trials for high-user, square and high-item graphs
	print "Starting tests"
	for u,i in ((30,30), (75,15), (15,75)):
		for params in (1,4,15):
			for fill in (0.8, 0.4, 0.2):
				trials.append({'params': params, 'fill': fill, 'users': u, 
							'items': i, 'rec': UserRecommender()})
				trials.append({'params': params, 'fill': fill, 'users': u, 
							'items': i, 'rec': ItemRecommender()})
				trials.append({'params': params, 'fill': fill, 'users': u, 
							'items': i, 'rec': MatrixRecommender()})
	for t in trials:
		params, fill, users, items = t['params'], t['fill'], t['users'], t['items']
		rec = t['rec'].create_recommender
		total_fails, total_correlation = 0, 0
		for i in range(num_tries):
			f, c = run_database_test(users,items,params,fill,50,rec)
			total_fails += f
			total_correlation += c
		failrate = total_fails / num_tries * 100
		avg_corr = total_correlation / num_tries
		print """Tests for %d users and %d items with %d params and %f percent given run
				with %s;  %f percent failed, %f correlation""" % \
				(users, items, params, fill*100, str(t['rec']), failrate, avg_corr)

