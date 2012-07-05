from __future__ import print_function, unicode_literals

import sqlite3 as sql

from persistent import Persistent
from BTrees.OOBTree import OOBTree

from nti.utils.transactions import ObjectDataManager

from nti.contentsearch.spambayes.classifier import _BaseWordInfo
from nti.contentsearch.spambayes.classifier import Classifier

from nti.contentsearch.spambayes import default_use_bigrams
from nti.contentsearch.spambayes import default_unknown_word_prob
from nti.contentsearch.spambayes import default_max_discriminators
from nti.contentsearch.spambayes import default_unknown_word_strength
from nti.contentsearch.spambayes import default_minimum_prob_strength

class PersistentWordInfo(Persistent, _BaseWordInfo):
	
	def __init__(self):
		self.spamcount = self.hamcount = 0
	
	
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

class SQL3Classifier(Classifier, ObjectDataManager):
	
	state_key = '__classifier state __'
	
	def __init__(self, dbpath, *args, **kwargs):
		Classifier.__init__(self, *args, **kwargs)
		ObjectDataManager.__init__(self, call=self._do_commit)
		self.dbpath = dbpath
		self._registered = False
		self._load(dbpath)

	def _do_commit(self): 
		self.db.commit()
		self._cursor = self.db.cursor()
	
	def abort(self, tx):
		self._cursor = self.db.cursor()
	
	def _create_db(self):
		bayes_table =  ("create table bayes ("
						"  word varchar(255) not null default '',"
						"  nspam integer not null default 0,"
						"  nham integer not null default 0,"
						"  primary key(word)" ");")
		self._cursor.execute(bayes_table)

	def _get_row(self, word):
		self._cursor.execute("select word, nspam, nham from bayes where word=?", (word,))
		rows = self._cursor.fetchall()
		return rows[0] if rows else {}

	def _set_row(self, word, nspam, nham):
		if self._has_key(word):
			self._cursor.execute("update bayes set nspam=?, nham=? "
					  			 "where word=?", (nspam, nham, word))
		else:
			self._cursor.execute("insert into bayes (nspam, nham, word) "
					  			 "values (?, ?, ?)", (nspam, nham, word))

	def _delete_row(self, word):
		self._cursor.execute("delete from bayes where word=?", (word,))

	def _has_key(self, key):
		self._cursor.execute("select word from bayes where word=?", (key,))
		rows = self._cursor.fetchall()
		return len(rows) > 0

	def _save_state(self):
		self._set_row(self.state_key, self.nspam, self.nham)
			
	def _load(self, dbpath):
		self.db = sql.connect(dbpath)
		self._cursor = self.db.cursor()
		self._registered = True
		self.transaction_manager.registerSynch(self)
		try:
			self._cursor.execute("select count(*) from bayes")
		except sql.OperationalError:
			self._create_db()

		if self._has_key(self.state_key):
			row = self._get_row(self.state_key)
			self.nspam = row[1]
			self.nham = row[2]
		else:
			self.nham = 0
			self.nspam = 0

	def close(self):
		if self._registered:
			self.transaction_manager.unregisterSynch(self)
			
	def newTransaction(self, t): 
		t.join(self)
	
	# ---------- 
	
	def _post_training(self):
		self._save_state()
		
	def _wordinfoget(self, word):
		word = unicode(word)
		row = self._get_row(word)
		if row:
			item = self.WordInfoClass()
			item.update(row[1], row[2])
			return item
		else:
			return self.WordInfoClass()
		
	get_record = _wordinfoget
		
	def _wordinfoset(self, word, record):
		word = unicode(word)
		self._set_row(word, record.spamcount, record.hamcount)

	def _wordinfodel(self, word):
		word = unicode(word)
		self._delete_row(word)

	def _wordinfokeys(self):
		self._cursor.execute("select word from bayes")
		rows = self._cursor.fetchall()
		return [r[0] for r in rows if r[0] != self.state_key]
	
	@property
	def words(self):
		return self._wordinfokeys()

