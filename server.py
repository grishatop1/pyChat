import socket
import time
import threading
import pickle
import json
import queue
import os
from transfer import Transfer
from filetransfer import FileReceiveServer

PATH = "uploads/"

class Client:
	def __init__(self, server, conn, addr, username, trans):
		self.server = server
		self.conn = conn
		self.addr = addr
		self.username = username
		self.trans = trans
		self.pingLock = queue.Queue(1)
		self.closed = False
		self.file = None
		threading.Thread(target=self.mainThread, daemon=True).start()
		threading.Thread(target=self.pinger, daemon=True).start()

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

			self.pingLock.put(True)

			content = pickle.loads(data)
			if content["type"] == "msg":
				self.handleMessages(content["data"])
				print(f"[{self.username}]: {content['data']}")
			elif content["type"] == "cmd":
				self.handleCommands(content["data"])
			elif content["type"] == "new-file":
				self.file = FileReceiveServer(self, content["id"], content["filename"],
									content["size"])
			elif content["type"] == "file":
				self.file.receive(content["data"])

		self.closeClient(reason)

	def sendDataPickle(self, obj):
		data = pickle.dumps(obj)
		self.trans.send(data)

	def handleMessages(self, content):
		data = pickle.dumps({"sender": self.username, "data": content, "type": "msg"})
		server.sendToAll(self.username, data)

	def handleCommands(self, cmd):
		if server.checkForOp(self.username):
			try:
				command = cmd[1:]
				parts = command.split(" ", 2)
			except:
				self.sendDataPickle({"type": "cmd-fail"})
				return
			if parts[0] == "kick":
				try:
					username = parts[1]
					server.kickUser(username)
				except:
					pass
			elif parts[0] == "op":
				try:
					username = parts[1]
					server.opUser(username)
				except:
					pass
			elif parts[0] == "ban":
				try:
					username = parts[1]
					server.banUser(username)
				except:
					pass
			elif parts[0] == "deop":
				try:
					username = parts[1]
					server.deOpUser(username)
				except:
					pass
			elif parts[0] == "unban":
				try:
					username = parts[1]
					server.deBanUser(username)
				except:
					pass
			elif parts[0] == "spam":
				threading.Thread(target=server.spamUsers, daemon=True).start()
			elif parts[0] == "list":
				users = server.returnOnlineUsers()
				self.sendDataPickle({"type":"info", "data":"Online:\n"+users})
			else:
				self.sendDataPickle({"type": "cmd-fail"})
				return
		else:
			self.sendDataPickle({"type": "no-permission"})

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
					self.closeClient("Timed out.")
				else:
					warn = True
					self.trans.send(b"ping")

	def closeClient(self, reason=""):
		if not self.closed:
			self.closed = True
			self.pingLock.put(False)
			self.conn.close()
			del server.clients[self.username]
			announce = pickle.dumps({"type": "gone", "username": self.username})
			server.sendToAll(None, announce)
			print(f"{self.username} disconnected. [{reason}]")


class Server:
	def __init__(self, ip, port):
		self.ip = ip
		self.port = port
		self.addr = (ip, port)
		self.running = True
		self.clients = {}

	def run(self):
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.bind(self.addr)
		self.s.listen()
		self.checkForJsonFiles("ops", "bans")
		self.checkForDirs(PATH)
		print(f"Server started on {self.addr}")
		self.acceptConnectionsLoop()

	def acceptConnectionsLoop(self):
		while True:
			conn, addr = self.s.accept()
			threading.Thread(target=self.createConnection, args=(conn, addr), 
				daemon=True).start()

	def checkUsername(self, username):
		if username in self.clients:
			return True
		else:
			return False

	def sendToAll(self, username, data, me=True):
		for client in self.clients:
			if not me:
				if client == username:
					continue
			trans = self.clients[client].trans
			trans.send(data)

	def createConnection(self, conn, addr):
		trans = Transfer(conn)
		username = trans.recvData()
		if username:
			username = username.decode()
		else:
			return
		if self.checkForBan(username):
			trans.send(b"ban")
			return
		if self.checkUsername(username):
			trans.send(b"username_already")
			return
		trans.send(b"accepted")
		self.clients[username] = Client(self, conn, addr, username, trans)
		announce = pickle.dumps({"type": "new", "username": username})
		self.sendToAll(None, announce)
		print(f"{username} connected!")

	def checkForJsonFiles(self, *filenames):
		for file in filenames:
			file += ".json"
			if not os.path.exists(file):
				with open(file, "a") as f:
					f.write("[]")
			else:
				with open(file, "r") as f:
					try:
						self.ops = json.load(f)
					except json.decoder.JSONDecodeError:
						with open(file, "w") as f_w:
							f_w.write("[]")

	def checkForOp(self, username):
		with open("ops.json", "r") as f:
			data = json.load(f)
			if username in data:
				return True
			else:
				return

	def checkForBan(self, username):
		with open("bans.json", "r") as f:
			data = json.load(f)
			if username in data:
				return True
			else:
				return

	def checkForDirs(self, *dirs):
		for _dir in dirs:
			try:
				os.makedirs(_dir)
			except:
				pass

	def appendToJson(self, file, obj):
		with open(file, "r") as f:
			data = json.load(f)
		data.append(obj)
		with open(file, "w") as f:
			json.dump(data, f)
	def removeFromJson(self, file, obj):
		with open(file, "r") as f:
			data = json.load(f)
		data.remove(obj)
		with open(file, "w") as f:
			json.dump(data, f)

	def kickUser(self, username):
		if username in self.clients:
			self.clients[username].trans.send(b"kick")
			self.clients[username].closeClient("Kicked.")

	def opUser(self, username):
		if self.checkForOp(username):
			return
		try:
			self.appendToJson("ops.json", username)
		except:
			return False

	def banUser(self, username):
		if self.checkForBan(username):
			return
		try:
			self.appendToJson("bans.json", username)
		except:
			return False
		try:
			self.clients[username].trans.send(b"banned")
			self.clients[username].closeClient("Banned")
		except:
			pass
	def deOpUser(self, username):
		if not self.checkForOp(username):
			return
		try:
			self.removeFromJson("ops.json", username)
		except:
			return False

	def deBanUser(self, username):
		if not self.checkForBan(username):
			return
		try:
			self.removeFromJson("bans.json", username)
		except:
			return False

	def spamUsers(self, count=50):
		data = pickle.dumps({"sender": "server", "data": "SERVER ULTRA SPAM", "type": "msg"})
		for _ in range(count):
			time.sleep(0.1)
			self.sendToAll("server", data)

	def returnOnlineUsers(self):
		clients = list(self.clients.keys())
		output = "\n".join(clients)
		return output

if __name__ == '__main__':
	ip = socket.gethostbyname(socket.gethostname())
	port = input("Enter port [Empty for 25565]: ")
	if not port:
		port = 25565
	else:
		port = int(port)
	server = Server(ip, port)
	server.run()