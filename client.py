import socket
import threading
import pickle
import queue
import time
from transfer import Transfer
from filetransfer import FileSend

class Client:
	def __init__(self, app):
		self.app = app
		self.connected = False
		self.file = None

	def createConnection(self, ip, port, username):
		self.username = username
		self.pingLock = queue.Queue(1)
		self.ip = ip
		self.port = port
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.settimeout(5)
		self.trans = Transfer(self.s)
		try:
			self.s.connect((self.ip, self.port))
		except socket.error:
			self.app.connection.connectionFailed("Couldn't connect to specified host.")
			return
		self.trans.send(username.encode())
		response = self.trans.recvData()
		self.s.settimeout(None)
		if response == b"accepted":
			self.connected = True
			threading.Thread(target=self.mainThread, daemon=True).start()
			threading.Thread(target=self.pinger, daemon=True).start()
			self.app.connection.connectionSuccess()
		elif response == b"username_already":
			self.app.connection.connectionFailed("Username is already taken.")
		elif response == b"ban":
			self.app.connection.connectionFailed("You were banned from this server.")
		else:
			self.app.connection.connectionFailed("An error was occured. :/")

	def sendFile(self, filepath):
		self.file = FileSend(self.trans, filepath)

	def sendMessage(self, msg):
		data = pickle.dumps({"type": "msg", "data": msg})
		threading.Thread(target=self.trans.send, args=(data,)).start()

	def sendCommand(self, cmd):
		data = pickle.dumps({"type": "cmd", "data": cmd})
		self.trans.send(data)

	def closeConnection(self, reason=""):
		if self.connected:
			self.connected = False
			self.s.shutdown(2)
			self.s.close()
			self.pingLock.put(False)
			self.app.connection.connectionLost(reason)

	def pinger(self):
		warn = False
		while True:
			try:
				response = self.pingLock.get(timeout=5)
				warn = False
				if not response:
					break
			except queue.Empty:
				if warn:
					self.closeConnection("Timed out.")
				else:
					warn = True
					self.trans.send(b"ping")

	def mainThread(self):
		reason = ""
		while True:
			data = self.trans.recvData()
			if not data:
				reason = "Connection lost."
				break
			if data == b"drop":
				reason = "Server closed connection."
				break
			elif data == b"ping":
				self.trans.send(b"pong")
				continue
			elif data == b"pong":
				self.pingLock.put(True)
				continue
			elif data == b"kick":
				reason = "You have been kicked from the server."
				break
			elif data == b"banned":
				reason = "You have been banned from the server."
				break
			elif data == b"timedout":
				reason = "Timed out."

			self.pingLock.put(True)

			content = pickle.loads(data)

			if content["type"] == "msg":
				sender, data = content["sender"], content["data"]
				self.app.chatlog.insertMessage(f"[{sender}]: {data}")
				if sender != self.username:
					threading.Thread(target=self.app.playMessageSound).start()
			elif content["type"] == "new":
				username = content["username"]
				self.app.chatlog.insertMessage(f"{username} connected.", "state")
			elif content["type"] == "gone":
				username = content["username"]
				self.app.chatlog.insertMessage(f"{username} disconnected.", "warning")
			elif content["type"] == "no-permission":
				self.app.chatlog.insertMessage(f"You have no permission to send commands.",
												"warning")
			elif content["type"] == "cmd-fail":
				self.app.chatlog.insertMessage(f"Invalid command.", "warning")
			elif content["type"] == "info":
				self.app.chatlog.insertMessage(content["data"], "blue")
			elif content["type"] == "file-progress":
				self.file.p = content["p"]
			elif content["type"] == "file-result":
				self.file.stop()
				if content["result"]:
					self.app.chatlog.insertMessage(f"File has been uploaded.", "info")
				else:
					self.app.chatlog.insertMessage(f"Uploading error.", "warning")

		self.closeConnection(reason)