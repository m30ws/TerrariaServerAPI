import terraria_api
from terraria_api import TerrariaAPI
import sys

ip = 'localhost'
port = 7777
passw = 'gamepasswd' # or ''/None

def main(args: list):
	terraria = TerrariaAPI(ip, port, passw)
	terraria.connect()

	print(f'\nConnected to {terraria.ip} : {terraria.port}')

if __name__=='__main__':
	main(sys.argv[1:])
