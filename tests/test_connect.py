from lib.mumble.client import MumbleClient
import time
client = MumbleClient()
print(client.get_session())
client.connect(host='localhost', username='ai-cube-1', pwd='Asdf12s34', port=12000)
time.sleep(2)
print(client.get_session())
print('----------- SLEEPING -----------------')
time.sleep(15)
client.disconnect()
print(client.get_session())