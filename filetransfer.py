import threading
import os
import time
import queue
import random
import pickle

TEMP_EXT = ".temporary"
PATH = "uploads/"

class FileReceive:
	def __init__(self, parent, _id, filename, size):
		self.parent = parent
		self.id = _id
		self.filename = filename
		self.filepath = PATH + filename
		self.size = size
		self.recv_size = 0
		self.active = True
		self.f = open(self.filepath + TEMP_EXT, "ab+")
		self.timeout_seconds = 10
		self.time = 0
		threading.Thread(target=self.timeout, daemon=True).start()

	def receive(self, data):
		self.time = 0
		self.recv_size += len(data)
		self.f.write(data)
		if self.recv_size == self.size:
			self.stop()

	def stop(self, success=True):
		if not self.active:
			return
		self.active = False
		self.f.close()
		if success:
			os.rename(self.filepath+TEMP_EXT, self.filepath)
		else:
			os.remove(self.filepath+TEMP_EXT)

	def timeout(self):
		while self.active:
			if self.time > self.timeout_seconds:
				self.stop(False)
				return
			else:
				self.time += 1
			time.sleep(1)

class FileSend:
	def __init__(self, trans, filepath):
		self.trans = trans
		self.filepath = filepath
		self.filename = os.path.basename(filepath)
		self.size = os.path.getsize(self.filepath)
		self.f = open(filepath, "rb")
		self.sending = True
		self.buffer = 1024 * 12
		self.sent_bytes = 0
		self.file_id = self.generateID()
		threading.Thread(target=self.sendThread, daemon=True).start()

	def generateID(self):
		return int(f"{random.randint(0,9)}"*4)

	def progress(self):
		return int(self.sent_bytes/self.size*100)

	def sendThread(self):
		pickled = pickle.dumps({"type": "new-file", 
								"id": self.file_id,
								"filename": self.filename,
								"size": self.size})
		self.trans.send(pickled)

		while self.sending:
			data = self.f.read(self.buffer)
			if data:
				pickled = pickle.dumps({"type": "file", "id": self.file_id, "data": data})
				self.trans.send(pickled, blocking=False)
				self.sent_bytes += len(data)
			else:
				self.stop()
				break

	def stop(self):
		self.f.close()
		self.sending = False