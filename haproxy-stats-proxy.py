#!/usr/bin/env python

import os
from os.path import isfile
import stat
import socket

from socket import error as SocketError

class Socket_wrap:
  def __init__(self, path, readonly = False, timeout = 3, bufsize = 1024):
    self.path = path
    self.readonly = readonly
    self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    self.timeout = timeout
    self.prompt = '> '
    self.bufsize = bufsize
  
  def connect(self):
    self._socket.connect(self.path)
    self._socket.settimeout(self.timeout)

    #Attempt to enter interactive mode in the HAProxy socket.
    try:
      self.send('prompt')
      self.wait()
      self.send('set timeout cli %d' % self.timeout)
      self.wait()
    except SocketError:
      raise SocketError('Could not connect and enter interactive mode for %s' % self.path)

  def _recv(self):
    data = self._socket.recv(self.bufsize)
    if not data:
      raise SocketError('Error while attempting to read socket %s' % self.path)
    return data

  def recv(self):
    readbuf = ''
    while not readbuf.endswith(self.prompt):
      data = self._recv()
      readbuf += data
    return readbuf.split('\n')[:-1]

  def wait(self):
    #toss data, waiting for prompt again
    readbuf = ''
    while not readbuf.endswith(self.prompt):
      data = self._recv()
      readbuf += data

  def send(self, message):
    self._socket.sendall('%s\n' % message)
  
  def close(self):
    try:
      self.send('quit')
    except:
      pass
    try:
      self._socket.close()
    except:
      pass
    

class HASockets:
  def __init__(self, sockets):
    self.sockets = sockets
    self.connected = []

  def connect(self):
    for sock in self.sockets:
      s = Socket_wrap(sock)
      s.connect()
      self.connected.append(s)

  def sendall(self, command):
    responses = []
    for s in self.connected:
      s.send(command)
      s = s.recv()
      sd = sock_resp_to_dict(s)
      print sd

def main(opts):
  sockets = find_sockets(opts.socketdir)
  for x in sockets:
    print "%s is a socket" % (x,)
  socks = HASockets(sockets)
  socks.connect()
  socks.sendall('show info')

def sock_resp_to_dict(resp):
  sock_dict = {}
  for item in resp:
    if item == "":
      continue
    k, v = item.split(":", 1)
    sock_dict[k] = v
  return sock_dict

def find_sockets(socketdir):
  sockets = [os.path.join(socketdir,f) for f in os.listdir(socketdir) if is_socket(os.path.join(socketdir,f)) ]
  return sockets

def is_socket(f_path):
  f_mode = os.stat(f_path).st_mode
  return stat.S_ISSOCK(f_mode)

if __name__ == '__main__':
  from optparse import OptionParser

  par = OptionParser()

  par.add_option('-s', '--socket-dir', dest='socketdir',
      default='/var/lib/haproxy/', help="Set haproxy socket dir")

  opts, args = par.parse_args()

  main(opts)
