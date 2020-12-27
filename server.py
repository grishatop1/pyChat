import socket
import time
import threading
import pickle
import queue
from transfer import Transfer

class Client:
	def __init__(self, conn, addr, username, trans):
		self.conn = conn
		self.addr = addr
		self.username = username
		self.trans = trans
		self.pingLock = queue.Queue(1)
		self.closed = False
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
			elif data == b"pong":
				self.pingLock.put(True)
				continue

			content = pickle.loads(data)
			if content["type"] == "msg":
				self.handleMessages(content["data"])
				print(f"[{self.username}]: {content['data']}")

		self.closeClient(reason)

	def handleMessages(self, content):
		data = pickle.dumps({"sender": self.username, "data": content, "type": "msg"})
		server.sendToAll(self.username, data)

	def pinger(self):
		while True:
			time.sleep(5)
			self.trans.send(b"ping")
			try:
				response = self.pingLock.get(timeout=5)
			except queue.Empty:
				self.closeClient("Timed out.")
			if not response:
				break

	def closeClient(self, reason=""):
		if not self.closed:
			self.closed = True
			self.pingLock.put(False)
			self.conn.close()
			del server.clients[self.username]
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
		print(f"Server started on {self.addr}")
		self.acceptConnectionsLoop()

	def acceptConnectionsLoop(self):
		while True:
			conn, addr = self.s.accept()
			threading.Thread(target=self.createConnection, args=(conn, addr), daemon=True).start()

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
		if self.checkUsername(username):
			trans.send(b"username_already")
			return
		trans.send(b"accepted")
		self.clients[username] = Client(conn, addr, username, trans)
		print(f"{username} connected!")

	def closeClient(self, lock, username, reason=""):
		lock.put(False)
		del self.clients[username]
		conn.shutdown(2)
		conn.close()
		print(f"{username} disconnected. [{reason}]")

if __name__ == '__main__':
	server = Server("192.168.0.33", 25565)
	server.run()