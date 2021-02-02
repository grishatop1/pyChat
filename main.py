import os
import threading
import time
from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showinfo
from tkinter.ttk import *

from playsound import playsound

from client import Client


class Connection(LabelFrame):
	def __init__(self, parent, *args, **kwargs):
		LabelFrame.__init__(self, parent, *args, **kwargs)
		self.parent = parent

		self.ip_label = Label(self, text="IP:")
		self.ip_entry = Combobox(self, values=["192.168.0.33"])
		self.ip_entry.insert(0, "192.168.0.33")
		self.port_label = Label(self, text="Port:")
		self.port_entry = Entry(self)
		self.port_entry.insert(0, "25565")
		self.username_label = Label(self, text="Username:")
		self.username_entry = Entry(self)
		self.connect_btn = Button(self, text="Connect", command=self.connect)

		self.ip_label.grid(row=0, column=0, padx=5, pady=5)
		self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
		self.port_label.grid(row=1, column=0, padx=5, pady=5)
		self.port_entry.grid(row=1, column=1, padx=5, pady=5)
		self.username_label.grid(row=2, column=0, padx=5, pady=5)
		self.username_entry.grid(row=2, column=1, padx=5, pady=5)
		self.connect_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

	def setConnectedState(self):
		self.ip_entry["state"] = "disabled"
		self.port_entry["state"] = "disabled"
		self.username_entry["state"] = "disabled"
		self.connect_btn.config(state="enabled", text="Disconnect", command=self.disconnect)

	def setNormalState(self):
		self.ip_entry["state"] = "enabled"
		self.port_entry["state"] = "enabled"
		self.username_entry["state"] = "enabled"
		self.connect_btn.config(state="enabled", text="Connect", command=self.connect)

	def setConnectingState(self):
		self.ip_entry["state"] = "disabled"
		self.port_entry["state"] = "disabled"
		self.username_entry["state"] = "disabled"
		root.focus()
		self.connect_btn.config(state="disabled", text="Connecting...")

	def connect(self):
		ip = self.ip_entry.get()
		port = int(self.port_entry.get())
		username = self.username_entry.get()
		self.setConnectingState()
		threading.Thread(target=client.createConnection, 
			args=(ip,port,username), daemon=True).start()

	def disconnect(self):
		client.closeConnection()

	def connectionSuccess(self):
		self.setConnectedState()
		showinfo("Connection", "Connected to the server!")

	def connectionFailed(self, reason=""):
		self.setNormalState()
		showinfo("Connection", f"Connection Failed.\n{reason}")

	def connectionLost(self, reason=""):
		self.setNormalState()
		showinfo("Connection", f"Disconnected.\n{reason}")

class ChatLog(LabelFrame):
	def __init__(self, parent, *args, **kwargs):
		LabelFrame.__init__(self, parent, *args, **kwargs)
		self.parent = parent

		self.chat = Text(self, width=30, wrap=WORD, state="disabled")
		self.chat.tag_config('info', foreground="green")
		self.chat.tag_config('warning', foreground="red")
		self.chat.tag_config('state', foreground="orange")
		self.chat.tag_config('blue', foreground="blue")

		self.msg_entry = Entry(self)
		self.msg_entry.bind("<Return>", self.sendMessage)
		self.msg_entry.bind("<KeyRelease>", self.keyup)
		self.send_btn = Button(self, text="Send", command=self.sendMessage)

		self.chat.grid(row=3, column=0, padx=5, pady=5)
		self.msg_entry.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
		self.send_btn.grid(row=5, column=0, padx=5, pady=5)

	def sendMessage(self, event=None):
		msg = self.msg_entry.get()
		if msg:
			if client.connected:
				client.sendMessage(msg)
			else:
				self.insertMessage(f"[Offline] - {msg}")

			self.msg_entry.delete(0, END)

	def sendCommand(self, event=None):
		cmd = self.msg_entry.get()
		if client.connected:
			client.sendCommand(cmd)
		else:
			self.insertMessage(f"You're offline dude.")
		self.msg_entry.delete(0, END)

	def insertMessage(self, message, state=None):
		self.chat["state"] = "normal"
		self.chat.insert(END, message + "\n", state)
		self.chat.see(END)
		self.chat["state"] = "disabled"

	def keyup(self, e):
		content = self.msg_entry.get()
		if content:
			if content[0] == "/":
				self.send_btn.config(text="Command", command=self.sendCommand)
				self.msg_entry.bind("<Return>", self.sendCommand)
			else:
				self.restartSend()
		else:
			self.restartSend()

	def restartSend(self):
		self.send_btn.config(text="Send", command=self.sendMessage)
		self.msg_entry.bind("<Return>", self.sendMessage)

class Files(LabelFrame):
	def __init__(self, parent, *args, **kwargs):
		LabelFrame.__init__(self, parent, *args, **kwargs)
		self.parent = parent
		self.uploading = False

		self.upload_btn = Button(self, text="Upload a file", command=self.upload)
		self.status = Label(self, text="Status: Idle")

		self.upload_btn.pack(padx=5, pady=5)
		self.status.pack(padx=5, pady=5)

	def setUploaded(self, filename, success):
		self.status["text"] = "Status: Idle"
		self.upload_btn.config(text="Upload a file", state="normal")
		self.uploading = False
		if success:
			showinfo("File", "File has been successfully uploaded.")
		else:
			showinfo("File", "Failed to upload the file. :(")

	def setUploading(self, filename):
		self.status["text"] = f"Uploading {filename} - 0%"
		self.upload_btn.config(text="Uploading...", state="disabled")
		self.uploading = True
	
	def updateStatus(self, filename, precent):
		self.status["text"] = f"Uploading {filename} - {precent}%"

	def upload(self):
		file = askopenfilename()
		filename = os.path.basename(file)
		if os.path.exists(file):
			self.status["text"] = f"Uploading - {filename}"
			client.sendFile(file)
			threading.Thread(target=self.progressThread, args=(filename,), 
			daemon=True).start()

	def progressThread(self, filename):
		self.setUploading(filename)
		while client.file.sending:
			progress = client.file.progress()
			self.updateStatus(filename, progress)
			time.sleep(0.5)
		self.setUploaded(filename, True)
		


class MainApplication(Frame):
	def __init__(self, parent, *args, **kwargs):
		Frame.__init__(self, parent, *args, **kwargs)
		self.parent = parent

		self.connection = Connection(self, text="Connection")
		self.chatlog = ChatLog(self, text="Chat")
		self.files = Files(self, text="File Transfer")

		self.connection.pack(padx=5, pady=5)
		self.chatlog.pack(padx=5, pady=5)
		self.files.pack(padx=5, pady=5, fill="x")

	def playMessageSound(self):
		playsound("msg.mp3")


if __name__ == "__main__":
	root = Tk()
	root.title("Chat")
	root.resizable(0,0)

	main = MainApplication(root)
	main.pack(side="top", fill="both", expand=True)

	client = Client(main)

	root.mainloop()
