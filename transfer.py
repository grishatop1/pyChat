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
		new = True
		full = b""
		received_len = 0
		received_head = 0
		recv_size = self.header
		while True:
			try:
				data = self.s.recv(recv_size)
			except socket.error:
				return
			if not data:
				return

			if new:
				received_head += len(data)
				if received_head < self.header:
					recv_size = self.header - len(data)
					continue
				actual_len = int(data[:self.header])
				full += data[self.header:]
				received_len += len(data)
				new = False
				continue

			full += data
			received_len += len(data)
			recv_size = min(max(actual_len - received_len + self.header, 0), self.buffer)

			if received_len - self.header == actual_len:
				break

		return full