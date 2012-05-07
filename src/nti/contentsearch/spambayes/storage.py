import sqlite3 as sql

from persistent import Persistent
from BTrees.OOBTree import OOBTree

from nti.contentsearch.spambayes.classifier import Classifier

from nti.contentsearch.spambayes import default_use_bigrams
from nti.contentsearch.spambayes import default_unknown_word_prob
from nti.contentsearch.spambayes import default_max_discriminators
from nti.contentsearch.spambayes import default_unknown_word_strength
from nti.contentsearch.spambayes import default_minimum_prob_strength

class PersistentWordInfo(Persistent):
	
	def __init__(self):
		self.spamcount = self.hamcount = 0
	
	def __repr__(self):
		return "WordInfo(%r %r)" % (self.spamcount, self.hamcount)
	
	
class PersistentClassifier(Persistent, Classifier):
	
	WordInfoClass = PersistentWordInfo
	
	def __init__(self, unknown_word_strength=default_unknown_word_strength, 
				 unknown_word_prob=default_unknown_word_prob, 
				 minimum_prob_strength=default_minimum_prob_strength, 
				 max_discriminators=default_max_discriminators, 
				 use_bigrams=default_use_bigrams, 
				 mapfactory=OOBTree):
		
		Classifier.__init__(self, unknown_word_strength, unknown_word_prob, minimum_prob_strength, 
							max_discriminators, use_bigrams, mapfactory)

			
PersistentBayes = PersistentClassifier

# -----------------------------------


class SQL3Classifier(Classifier):
	
	state_key = '__classifier state __'
	
	def __init__(self, dbpath, *args, **kwargs):
		super(SQL3Classifier, self).__init__(*args, **kwargs)
		self.dbpath = dbpath
		self._load(dbpath)
	
	def cursor(self):
		return self.db.cursor()
	
	def fetchall(self, c):
		return c.fetchall()
	
	def commit(self, c):
		self.db.commit()

	# ---------- 
	
	def _create_db(self):
		bayes_table =  ("create table bayes ("
						"  word varchar(255) not null default '',"
						"  nspam integer not null default 0,"
						"  nham integer not null default 0,"
						"  primary key(word)" ");")
		c = self.cursor()
		c.execute(bayes_table)
		self.commit(c)

	def _get_row(self, word):
		c = self.cursor()
		c.execute("select * from bayes where word=%s", (word,))
		rows = self.fetchall(c)
		return rows[0] if rows else {}

	def _set_row(self, word, nspam, nham):
		c = self.cursor()
		if self._has_key(word):
			c.execute("update bayes"
					  "  set nspam=%s,nham=%s"
					  "  where word=%s",
					  (nspam, nham, word))
		else:
			c.execute("insert into bayes"
					  "  (nspam, nham, word)"
					  "  values (%s, %s, %s)",
					  (nspam, nham, word))
		self.commit(c)

	def _delete_row(self, word):
		c = self.cursor()
		c.execute("delete from bayes where word=%s", (word,))
		self.commit(c)

	def _has_key(self, key):
		c = self.cursor()
		c.execute("select word from bayes where word=%s", (key,))
		return len(self.fetchall(c)) > 0

	def _save_state(self):
		self._set_row(self.statekey, self.nspam, self.nham)
			
	def _load(self, dbpath):
		self.db = sql.connect(dbpath)
		try:
			c = self.db.cursor()
			c.execute("select count(*) from bayes")
		except sql.OperationalError:
			self.create_bayes()

		if self._has_key(self.statekey):
			row = self._get_row(self.statekey)
			self.nspam = row["nspam"]
			self.nham = row["nham"]
		else:
			self.nham = 0
			self.nspam = 0

	# ---------- 
			
	def _encode(self, word):
		if isinstance(word, unicode):
			word = word.encode("utf-8")
		return word
	
	def _post_training(self):
		self._save_state()
		
	def _wordinfoget(self, word):
		word = self._encode(word)
		row = self._get_row(word)
		if row:
			item = self.WordInfoClass()
			item.__setstate__((row["nspam"], row["nham"]))
			return item
		else:
			return self.WordInfoClass()
		
	def _wordinfoset(self, word, record):
		word = self._encode(word)
		self._set_row(word, record.spamcount, record.hamcount)

	def _wordinfodel(self, word):
		word = self._encode(word)
		self._delete_row(word)

	def _wordinfokeys(self):
		c = self.cursor()
		c.execute("select word from bayes")
		rows = self.fetchall(c)
		return [r[0] for r in rows if r[0] != self.state_key]

