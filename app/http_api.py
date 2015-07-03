"""
ExaBGP HTTP API

This is a hacky solution to allow a remote process (eabgpmon) to make calls to ExaBGP
It should eventually be replaced with reading to/from a named pipe or something using
a queue handler (RabbitMQ, Redis, etc.)

Receives an HTTP POST with a command and prints it to the STDIN process ExaBGP is
reading. Does no sort of validation or response checking from ExaBGP.

"""

import cgi
import SimpleHTTPServer
import SocketServer
from sys import stdout
 
PORT = 5001
 
class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
 
    def createResponse(self, command):
        """ Send command string back as confirmation """
        self.send_response(200)
        self.send_header('Content-Type', 'application/text')
        self.end_headers()
        self.wfile.write(command)
        self.wfile.close()
 
    def do_POST(self):
        """ Process command from POST and output to STDOUT """
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST'})
        command = form.getvalue('command')
        stdout.write('%s\n' % command)
        stdout.flush()
        self.createResponse('Success: %s' % command)
 
handler = ServerHandler
httpd = SocketServer.TCPServer(('', PORT), handler)
stdout.write('serving at port %s\n' % PORT)
stdout.flush()
httpd.serve_forever()