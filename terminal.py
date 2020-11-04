import socket
import pickle
import time

PORT = 10001

#=============================================================================================
    
    

        
#=============================================================================================


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', PORT))

input_buffer = object()
output_buffer = 'belepes Imre kulcs'

s.send(bytes(output_buffer, 'utf-8'))

while True:
  #Fogad
    msg = s.recv(2048)
    data_in = pickle.loads(msg)
    for i in range(len(data_in)):
        print(data_in[i])
    output_buffer = input("ImreApp]->Terminal:-$ ")
    if output_buffer == '':
        output_buffer = 'nope'
  #Kuld
    data_out = bytes(output_buffer, 'utf-8')
    s.send(data_out)
    time.sleep(0.01)

exit()