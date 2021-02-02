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

	def send(self, data, blocking=True):
		h_data = self.appendHeader(data)
		if blocking:
			lock = queue.Queue()
			self.pending.put([lock, h_data])
			result = lock.get()
			return result
		else:
			self.pending.put([None, h_data])

	def sendDataLoop(self):
		while True:
			lock, data = self.pending.get()
			try:
				self.s.send(data)
				if lock:
					lock.put(True)
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