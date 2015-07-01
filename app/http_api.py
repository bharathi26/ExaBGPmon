"""
ExaBGP HTTP API

This is a hacky solution to allow a remote process (eabgpmon) to make calls to ExaBGP
It should eventually be replaced with reading to/from a named pipe or something using
a queue handler (RabbitMQ, Redis, etc.)

Receives an HTTP POST with a command and prints it to the STDIN process ExaBGP is
reading. Does no sort of validation or response checking from ExaBGP.

"""

from flask import Flask, request
from sys import stdout
 
app = Flask(__name__)
 
# Setup a command route to listen for prefix advertisements
@app.route('/', methods=['POST'])
def command():
 
    command = request.form['command']
    stdout.write('%s\n' % command)
    stdout.flush()
     
    return 'Success: %s\n' % command
 
if __name__ == '__main__':
    app.run(port=5001, debug=False)