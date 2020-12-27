import socket
import threading
import pickle
import queue
import time
from transfer import Transfer

class Client:
	def __init__(self, app):
		self.app = app
		self.connected = False

	def createConnection(self, ip, port, username):
		self.username = username
		self.pingLock = queue.Queue(1)
		self.ip = ip
		self.port = port
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.trans = Transfer(self.s)
		try:
			self.s.connect((self.ip, self.port))
		except socket.error:
			self.app.connection.connectionFailed("Couldn't connect to specified host.")
			return
		self.trans.send(username.encode())
		response = self.trans.recvData()
		if response == b"accepted":
			self.connected = True
			threading.Thread(target=self.mainThread, daemon=True).start()
			threading.Thread(target=self.pinger, daemon=True).start()
			self.app.connection.connectionSuccess()
		elif response == b"username_already":
			self.app.connection.connectionFailed("Username is already taken.")
		else:
			self.app.connection.connectionFailed("An error was occured. :/")

	def sendMessage(self, msg):
		data = pickle.dumps({"type": "msg", "data": msg})
		self.trans.send(data)

	def closeConnection(self, reason=""):
		if self.connected:
			self.connected = False
			self.s.shutdown(2)
			self.s.close()
			self.app.connection.connectionLost(reason)

	def pinger(self):
		while True:
			time.sleep(5)
			self.trans.send(b"ping")
			try:
				response = self.pingLock.get(timeout=5)
			except queue.Empty:
				self.closeConnection("Server timed out.")
			if not response:
				break

	def mainThread(self):
		reason = ""
		while True:
			data = self.trans.recvData()
			if not data:
				reason = "Disconnection"
				break
			if data == b"drop":
				reason = "Client disconnected"
				break
			elif data == b"ping":
				self.trans.send(b"pong")
				continue
			elif data == b"pong":
				self.pingLock.put(True)
				continue

			content = pickle.loads(data)

			if content["type"] == "msg":
				sender, data = content["sender"], content["data"]
				self.app.chatlog.insertMessage(f"[{sender}]: {data}")