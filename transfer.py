import socket
import threading
import queue

class Transfer:
	def __init__(self, sock):
		self.s = sock
		self.pending = queue.Queue()
		self.header = 12
		self.buffer = 1024
		threading.Thread(target=self.sendDataLoop, daemon=True).start()

	def appendHeader(self, data):
		data_len = len(data)
		header = str(data_len).encode() + (self.header - len(str(data_len))) * b" "
		return header + data

	def send(self, data):
		h_data = self.appendHeader(data)
		self.pending.put(h_data)

	def sendRaw(self, data):
		self.pending.put(data)

	def sendDataLoop(self):
		while True:
			data = self.pending.get()
			try:
				self.s.send(data)
			except socket.error:
				return

	def recvData(self):
		full = b""
		recv_len = 0
		recv_size = self.header
		new = True
		while True:
			if recv_size == 0:
				break
			try:
				data = self.s.recv(recv_size)
			except socket.error:
				return
			if not data:
				return

			if new:
				actual_len = int(data[:self.header])
				full += data[self.header:]
				recv_len += len(data[self.header:])
				recv_size = min(actual_len - recv_len, self.buffer)
				new = False
				continue

			full += data
			recv_len += len(data)
			recv_size = min(actual_len - recv_len, self.buffer)

		return full