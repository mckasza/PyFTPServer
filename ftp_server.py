import socket
import threading
import time
import select
import pathlib
import stat
import datetime

class ClientThread(threading.Thread):
	def __init__(self, client_connection, address, stop_event):
		super().__init__(daemon=True)
		self.client_connection = client_connection
		self.stop_event = stop_event
	
	def run(self):
		self.client_connection.sendall(b'220 (FTP Server)\r\n')
		passive_conn = None
		passive_address = None
	
		while True:
			readable = select.select([self.client_connection], [], [], 0.1)[0]
			
			if self.client_connection in readable:
				data = self.client_connection.recv(1024)
				if len(data) == 0:
					break
					
				if data[0:4] == b'USER':
					self.client_connection.sendall(b'331 Please specifiy the password.\r\n')
				if data[0:4] == b'PASS':
					self.client_connection.sendall(b'230 Login Successful.\r\n')
				elif data[0:4] == b'SYST':
					self.client_connection.sendall(b'215 UNIX Type: L8\r\n')
				elif data[0:3] == b'PWD':
					self.client_connection.sendall(b'257 "/"\r\n')
				elif data[0:6] == b'TYPE I':
					self.client_connection.sendall(b'200 Switching to Binary mode.\r\n')
				elif data[0:4] == b'SIZE':
					self.client_connection.sendall(b'550 Could not get file size.\r\n')
				elif data[0:3] == b'CWD':
					self.client_connection.sendall(b'250 Directory successfully changed.\r\n')
				elif data[0:4] == b'PASV':
					passive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					passive_socket.bind(('127.0.0.1', 0))
					
					port = passive_socket.getsockname()[1]
					port_high = int(port/256)
					port_low = port-256*int(port/256)
					
					self.client_connection.sendall(bytes('227 Entering Passive Mode (127,0,0,1,{},{}).\r\n'.format(port_high, port_low), 'utf-8'))
					
					passive_socket.listen()
					passive_conn, passive_address = passive_socket.accept()
				elif data[0:4] == b'LIST':
						self.client_connection.sendall(b'150 Here comes the directory listing.\r\n')
						
						directory_listing = []
						for item in pathlib.Path.cwd().iterdir():
							filestat = item.stat()
							mode = stat.filemode(filestat.st_mode)
							hard_links = filestat.st_nlink
							user_id = filestat.st_uid
							group_id = filestat.st_gid
							size = filestat.st_size
							mod_time = datetime.datetime.fromtimestamp(filestat.st_mtime).strftime('%b %d  %Y')
							filename = item.relative_to(pathlib.Path.cwd())
							
							line = f'{mode}'+' '*4+f'{hard_links} {user_id}'+' '*8+f'{group_id}'+' '*8+f'{size} {mod_time} {filename}'
							directory_listing.append(line)
							
						passive_conn.sendall(bytes('\r\n'.join(directory_listing)+'\r\n', 'utf-8'))
						passive_conn.close()
						
						self.client_connection.sendall(b'226 Directory send OK.\r\n')
				elif data[0:4] == b'QUIT':
					self.client_connection.close()
					break
						
			if self.stop_event.is_set():
				if passive_conn:
					passive_conn.close()
				break
				
		
		
try:
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setblocking(False)
	server_socket.bind(('127.0.0.1', 21))
	server_socket.listen()

	stop_event = threading.Event()
	
	client_threads = []
	
	while True:
		readable = select.select([server_socket], [], [], 0.1)[0]
		
		if server_socket in readable:
			conn, address = server_socket.accept()
			
			client_thread = ClientThread(conn, address, stop_event)
			client_threads.append(client_thread)
			client_thread.start()
			
		for thread in client_threads:
			if thread.is_alive():
				thread.join(0.1)
			
except KeyboardInterrupt:
	stop_event.set()
	
	for thread in client_threads:
		if thread.is_alive():
			thread.join()
		
	server_socket.close()
		
