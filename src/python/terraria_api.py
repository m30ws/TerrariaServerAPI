import atexit
import enum
import time
import socket
import struct
import sys

class TTypes(enum.Enum):
	"""
	Types recognized by Terraria server

	|  Type  | Bytes | Notes                                                  |
	|--------|-------|--------------------------------------------------------|
	| Byte   |   1   | Unsigned 0 .. 255                                      |
	| Int16  |   2   | Signed -32,768 .. 32,767                               |
	| Int32  |   4   | Signed -2,147,483,648 .. 2,147,483,647                 |
	| Single |   4   | Single precision float                                 |
	| Color  |   3   | Three unsigned bytes that define R,G,B values          |
	| String |   *   | ASCII string, length must be derived from message size |
	"""
	
	Byte   = enum.auto()
	Int16  = enum.auto()
	Int32  = enum.auto()
	Single = enum.auto()
	Color  = enum.auto()
	String = enum.auto()


	@classmethod
	def to_bytes_as_type(TTypes, value, typ):
		""" """

		if not isinstance(typ, TTypes):
			print(f'Unknown type ({typ})')
			return None

		# '<' = little
		# '>' = big
		endian = '<'

		try:
			retval = None

			if typ == TTypes.Byte:
				retval = struct.pack(f'<c', bytes([value])) # capture exc if invalid value

			elif typ == TTypes.Int16:
				retval = struct.pack(f'{endian}h', value)

			elif typ == TTypes.Int32:
				retval = struct.pack(f'{endian}i', value)

			elif typ == TTypes.Single:
				retval = struct.pack(f'{endian}f', value)

			elif typ == TTypes.Color:
				if len(value) > 3:
					value = value[:3]
				retval = struct.pack(f'{endian}bbb', *value)

			elif typ == TTypes.String:
				str_enc = value.encode(encoding='utf-8')
				retval = TTypes.to_bytes_as_type( len(str_enc), TTypes.Byte) \
							+ str_enc

			return retval

		except Exception as e:
			print(f'[error] to_bytes conversion error: {e}')
			return None


	@classmethod
	def from_bytes_as_type(TTypes, value, typ):
		""" """

		if not isinstance(typ, TTypes):
			print(f'Unknown type ({typ})')
			return None

		# '<' = little
		# '>' = big
		endian = '<'

		try:
			retval = None

			if typ == TTypes.Byte:
				retval = struct.unpack(f'B', value)[0] # capture exc if invalid value

			elif typ == TTypes.Int16:
				retval = struct.unpack(f'{endian}h', value)[0]

			elif typ == TTypes.Int32:
				retval = struct.unpack(f'{endian}i', value)[0]

			elif typ == TTypes.Single:
				retval = struct.unpack(f'{endian}f', value)[0]

			elif typ == TTypes.Color:
				retval = struct.unpack(f'{endian}bbb', value)

			elif typ == TTypes.String:
				retval = value[1:].decode(encoding='utf-8') # contains 1(?) byte for size at the start

			return retval

		except Exception as e:
			print(f'[error] from_bytes conversion error: {e}')
			return None


class TMessageTypes(enum.IntEnum):
	""" """
	CONNECTION_REQUEST           = 0x01
	FATAL_ERROR                  = 0x02
	CONNECTION_APPROVED          = 0x03
	PLAYER_APPEARANCE            = 0x04
	SET_INVENTORY                = 0x05
	REQUEST_WORLD_INFO           = 0x06
	WORLD_INFO                   = 0x07
	REQUEST_INITIAL_TILE_DATA    = 0x08
	STATUSBAR_TEXT               = 0x09
	TILE_ROW_DATA                = 0x0A
	RECALCULATE_UV               = 0x0B
	SPAWN_PLAYER                 = 0x0C
	PLAYER_CONTROL               = 0x0D
	SET_PLAYER_ACTIVITY          = 0x0E
	UNUSED                       = 0x0F
	SET_PLAYER_LIFE              = 0x10
	MODIFY_TILE                  = 0x11
	SET_TIME                     = 0x12
	OPEN_CLOSE_DOOR              = 0x13
	TILE_BLOCK                   = 0x14
	UPDATE_ITEM                  = 0x15
	SET_OWNER_OF_ITEM            = 0x16
	UPDATE_NPC                   = 0x17
	STRIKE_NPC                   = 0x18
	CHAT                         = 0x19
	DAMAGE_PLAYER_OR_PVP         = 0x1A
	UPDATE_PROJECTILE            = 0x1B
	DAMAGE_NPC                   = 0x1C
	DESTROY_PROJECTILE           = 0x1D
	TOGGLE_PVP                   = 0x1E
	REQUEST_OPEN_CHEST           = 0x1F
	SET_CHEST_ITEM               = 0x20
	OPEN_CLOSE_CHEST             = 0x21
	DESTROY_CHEST                = 0x22
	HEAL_PLAYER                  = 0x23  # Sent when the player uses a potion or heals himself somehow.
	SET_ZONES                    = 0x24
	REQUEST_PASSWORD             = 0x25
	RESPOND_PASSWORD             = 0x26
	UNASSIGN_ITEM                = 0x27
	TALK_TO_NPC                  = 0x28
	ANIMATE_PLAYER_FLAIL         = 0x29
	SET_PLAYER_MANA              = 0x2A
	REPLENISH_MANA               = 0x2B
	KILL_PLAYER                  = 0x2C
	CHANGE_PARTY                 = 0x2D
	READ_SIGN                    = 0x2E
	SET_SIGN_TEXT                = 0x2F
	ADJUST_LIQUID                = 0x30
	SPAWN                        = 0x31
	SET_PLAYER_BUFFS             = 0x32
	OLD_MANS_ANSWER              = 0x33
	UNLOCK_CHEST_OR_DOOR         = 0x34
	ADD_NPC_BUFF                 = 0x35
	SET_NPC_BUFFS                = 0x36
	ADD_PLAYER_BUFF              = 0x37
	SET_NPC_NAME                 = 0x38
	SET_BALANCE_STATS            = 0x39
	PLAY_HARP                    = 0x3A
	FLIP_SWITCH                  = 0x3B
	MOVE_NPC_HOME                = 0x3C
	SUMMON_BOSS_OR_INVASION      = 0x3D
	NINJA_SHADOW_DODGE           = 0x3E
	PAINT_TILE                   = 0x3F
	PAINT_WALL                   = 0x40
	TELEPORT_PLAYER_NPC          = 0x41
	QUICK_HEAL_PLAYER            = 0x42  # Sent when client heals himself
	UNKNOWN                      = 0x44


class TerrariaAPI:
	""" """

	def __init__(self, ip: str = None, port: int = None, password: str = None):
		""" """
		self.TERRARIA_DEFAULT_IP = 'localhost'
		self.TERRARIA_DEFAULT_PORT = 7777
		self.TERRARIA_PROTO_VER = 'Terraria279' ##
		
		self.TERRARIA_TIMEOUT = 20#s

		self.ip = None
		self.sockaddr = None # is set through socket.getaddrinfo
		self.port = None
		self.sock = None
		self.password = password

		self.last_msg = b''

		self.set_address(ip, port)
		atexit.register(self.disconnect)

	
	def timed_out(self, *args, **kwargs):
		""" """
		print(f'Timeout encountered: {args}, {kwargs}')

	
	def set_ip(self, ip: str = None):
		""" Sets IP address, uses TERRARIA_DEFAULT_IP if None """

		self.ip = ip
		if ip is None:
			self.ip = self.TERRARIA_DEFAULT_IP

	
	def set_port(self, port: int = None):
		""" Sets port, uses TERRARIA_DEFAULT_PORT if None """
		
		self.port = port
		if port is None:
			self.port = self.TERRARIA_DEFAULT_PORT

	
	def set_address(self, ip: str = None, port: int = None):
		""" Sets both IP address and port, if an argument is None it is skipped. """
		
		if ip is not None:
			self.set_ip(ip)
		
		if port is not None:
			self.set_port(port)

	
	def connect(self, ip: str = None, port: int = None) -> bool:
		""" """
		self.set_address(ip, port)

		if self.sock is not None:
			self.disconnect()

		try:
			addrinfo = socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM)

			for addr in addrinfo:
				family, stype, proto, _, sockaddr = addr
				try:
					self.sock = socket.socket(family, stype, proto)
					self.sock.settimeout(self.TERRARIA_TIMEOUT)

				except Exception as e:
					print(f'[info] Cannot resolve {self.ip}... ({e})')
					continue

				try:
					self.sock.connect(sockaddr)
					self.sockaddr = sockaddr

				except Exception as e:
					print(f'[error] Error during connection: {e}')
					self.sock.close()
					self.sock = None
					return False

			if self.sock is None:
				print(f'[error] Cannot connect to {self.ip}')
				return False

			print('[info] Initialized socket.')

			self.tconnect() # initiate tserver connection

			return True

		except socket.timeout as e:
			self.timed_out()
		except socket.error as e:
			print('Socket error: {e}')

		return False

	
	def disconnect(self):
		""" Disconnects and cleans up the socket """

		if self.sock is not None:
			self.tdisconnect()

			# Destroy socket
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
			self.sock = None
		
		self.sockaddr = None

	
	def serverthread_func(self, *args, **kwargs):
		"""  """
		pass
	
	
	def tconnect(self, *args, **kwargs) -> int:
		""" Begin Terraria connect protocol with the connected server
			Return values:
				 0 = ok
				-1 = invalid socket
				-2 = ip banned
				-3 = unknown error (unknown message received)
		"""

		if self.sock is not None:
			rv = self.tsend(TMessageTypes.CONNECTION_REQUEST, self.TERRARIA_PROTO_VER)
			print(f'[info] send status: {rv}')
			
			typ, data, data_ln = self.trecv()
			print(f'> Connection req response: {typ.name} ({hex(typ)})')
			
			if typ == TMessageTypes.REQUEST_PASSWORD:
				print(f'[msg] Sending password to server...')
				self.tsend(TMessageTypes.RESPOND_PASSWORD, self.password)
			elif typ == TMessageTypes.FATAL_ERROR:
				print(f'[msg] You were banned from this server :(')
				return -2
			else:
				print(f'[error] Unexpected message received ({typ})')
				return -3

			typ, data, data_ln = self.trecv()
			print(f'> Password sent response: {data} ({typ.name})')

			if typ == TMessageTypes.FATAL_ERROR:
				# print(f'[error] Fatal error ({typ}, {data}, {data_ln})')
				print(f'[msg] Password incorrect :(')
				return -2
			elif typ != TMessageTypes.CONNECTION_APPROVED:
				print(f'[error] Unexpected message received ({typ})')
				return -3

			self.player_slot = TTypes.to_bytes_as_type(data[0], TTypes.Byte)
			print(f'[msg] Player slot: {self.player_slot} ({type(self.player_slot)})')
			print(f'[msg] Password accepted, initializing...')

			# TODO: finish login
			print(f'[msg] Sending player data... [.TODO.]\n')


			return 0

		return -1  # socket is NULL or other error

	
	def tdisconnect(self, *args, **kwargs) -> bool:
		""" Begin Terraria disconnect protocol with the connected server """
		if self.sock is not None:
			# self.tsend( )
			return True
		return False # socket is NULL or other error

	
	def tsend(self, mtype, payload: 'str|bytes' = None) -> bool:
		""" """
		if mtype not in TMessageTypes:
			print(f'[warning] message type not found in TMessageTypes')
			# but allow it

		if payload is None:
			print(f'[warning] using empty payload')
			payload = b''

		try:
			mtype = TTypes.to_bytes_as_type(mtype, TTypes.Byte)
		except Exception as e:
			print(f'[error] send converting lengths to bytes: {e}')
			return False

		prepared_msg = mtype

		try:
			if isinstance(payload, str):
				prepared_msg += TTypes.to_bytes_as_type(payload, TTypes.String)
			elif isinstance(payload, bytes):
				prepared_msg += payload
			else:
				raise Exception(f'Invalid payload type: {type(payload)}, should be either str or bytes.')

		except Exception as e:
			print(f'[error] send preparing msg: {e}')
			return False

		print('[debug] prepared_msg:', prepared_msg)
		
		total_len = TTypes.to_bytes_as_type(2 + len(prepared_msg), TTypes.Int16)
		prepared_msg = total_len + prepared_msg # prepend whole length to the msg

		print('[debug] prepared_msg:', prepared_msg)

		try:
			self.sock.sendall(prepared_msg)
			self.last_msg = prepared_msg
			return True
		except Exception as e:
			print(f'[error] send message sendall: {e}')
			return False


	def trecv(self):
		""" """
		# Read message size
		try:
			total_msg_len = self.sock.recv(2)
			total_msg_len = TTypes.from_bytes_as_type(total_msg_len, TTypes.Int16)
		except Exception as e:
			print(f'[error] recv message len failed: {e}')
			return None

		msg_len = total_msg_len
		if msg_len < 3:
			print(f'[error] recv message smaller than minimal size')
			return None

		msg_len -= 2

		try:
			msg_type = self.sock.recv(1)
			msg_type = TTypes.from_bytes_as_type(msg_type, TTypes.Byte)
		except Exception as e:
			print(f'[error] recv reading message type: {e}')
			return None

		msg_len -= 1

		if msg_len > 0:
			try:
				return TMessageTypes(msg_type), self.sock.recv(msg_len), msg_len
			except Exception as e:
				print(f'[error] recv while reading payload: {e}')
				return None
		else:
			return TMessageTypes(msg_type), b'', 0

