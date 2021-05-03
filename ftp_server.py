import tkinter as tk
import socket
import threading
import time
import select
import pathlib
import stat
import datetime
			
try:
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setblocking(False)
	server_socket.bind(('127.0.0.1', 21))
	server_socket.listen()

	while True:
		readable = select.select([server_socket], [], [], 0.25)[0]
		
		if server_socket in readable:
			conn, address = server_socket.accept()
			
			conn.sendall(b'220 (FTP Server)\r\n')
			passive_conn = None
			passive_address = None
			
			while True:
				readable, writeable, exception = select.select([conn], [], [], 0.25)
				
				if conn in readable:
					data = conn.recv(1024)
					if len(data) == 0:
						break
						
					if data[0:4] == b'USER':
						conn.sendall(b'331 Please specifiy the password.\r\n')
					if data[0:4] == b'PASS':
						conn.sendall(b'230 Login Successful.\r\n')
					elif data[0:4] == b'SYST':
						conn.sendall(b'215 UNIX Type: L8\r\n')
					elif data[0:3] == b'PWD':
						conn.sendall(b'257 "/"\r\n')
					elif data[0:6] == b'TYPE I':
						conn.sendall(b'200 Switching to Binary mode.\r\n')
					elif data[0:4] == b'SIZE':
						conn.sendall(b'550 Could not get file size.\r\n')
					elif data[0:3] == b'CWD':
						conn.sendall(b'250 Directory successfully changed.\r\n')
					elif data[0:4] == b'PASV':
						passive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						passive_socket.settimeout(15)
						passive_socket.bind(('127.0.0.1', 0))
						
						port = passive_socket.getsockname()[1]
						print(port)
						port_high = int(port/256)
						port_low = port-256*int(port/256)
						
						conn.sendall(bytes('227 Entering Passive Mode (127,0,0,1,{},{}).\r\n'.format(port_high, port_low), 'utf-8'))
						
						passive_socket.listen()
						passive_conn, passive_address = passive_socket.accept()
					elif data[0:4] == b'LIST':
						conn.sendall(b'150 Here comes the directory listing.\r\n')
						
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
						
						conn.sendall(b'226 Directory send OK.\r\n')
						
	server_socket.close()
			
except KeyboardInterrupt:
	server_socket.close()
		
