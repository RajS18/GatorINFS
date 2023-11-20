from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
BLOCK_SIZE = 256
import time

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


if __name__ == "__main__":

  block = []
  block.insert(0,bytearray(BLOCK_SIZE))

  # Create server
  server = SimpleXMLRPCServer(('localhost', 8000),
                        requestHandler=RequestHandler) 

  def Put(value):
    block[0] = value
    return 0

  server.register_function(Put, 'Put')

  def Get(key):
    time.sleep(7)
    if key == 0:
      return block[key]
    else:
      return -1

  server.register_function(Get, 'Get')

  # Run the server's main loop
  server.serve_forever()

