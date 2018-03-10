import curses
import threading
import time
import zmq
import sys
import re

def threadrec(sub):
    while True:
        recvString = sub.recv_string()
        regex = re.compile(sys.argv[1], re.IGNORECASE)
        if re.match(regex , recvString):
            pass
        else :
            print (recvString)

def threadsend(chat_sender):
    while True:
        s = input ("["+sys.argv[1]+"] >")
        chat_sender.send_string(s)

class ClientChat(object):

    def __init__(self, username, server_host, server_port, chat_pipe):
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.context = zmq.Context()
        self.ch_socket = None
        self.chat_pipe = chat_pipe
        self.poller = zmq.Poller()

    def connect_to_server(self):
        self.ch_socket = self.context.socket(zmq.REQ)
        connect_string = 'tcp://{}:{}'.format(
            self.server_host, self.server_port)
        self.ch_socket.connect(connect_string)

    def reconnect_to_server(self):
        self.poller.unregister(self.ch_socket)
        self.ch_socket.setsockopt(zmq.LINGER, 0)
        self.ch_socket.close()
        self.connect_to_server()
        self.register_with_poller()

    def register_with_poller(self):
        self.poller.register(self.ch_socket, zmq.POLLIN)

    def prompt_for_message(self):
        return self.chat_pipe.recv_string()

    def send_message(self, message):
        data = {
            'username': self.username,
            'message': message,
        }
        self.ch_socket.send_json(data)

    def get_reply(self):
        self.ch_socket.recv()

    def has_message(self):
        events = dict(self.poller.poll(3000))
        return events.get(self.ch_socket) == zmq.POLLIN

    def start_main_loop(self):
        self.connect_to_server()
        self.register_with_poller()

        while True:
            message = self.prompt_for_message()
            self.send_message(message)
            if self.has_message():
                self.get_reply()
            else:
                self.reconnect_to_server()

    def run(self):
        thread = threading.Thread(target=self.start_main_loop)
        # make sure this background thread is daemonized
        # so that when user sends interrupt, whole program stops
        thread.daemon = True
        thread.start()

class ClientSub(object):

    def __init__(self, server_host, server_port, sub_pipe):
        self.server_host = server_host
        self.server_port = server_port
        self.context = zmq.Context()
        self.pub_sock = None
        self.sub_pipe = sub_pipe
        self.poller = zmq.Poller()

    def connect_to_server(self):
        self.pub_sock = self.context.socket(zmq.SUB)
        self.pub_sock.setsockopt_string(zmq.SUBSCRIBE, '')
        connect_string = 'tcp://{}:{}'.format(
            self.server_host, self.server_port)
        self.pub_sock.connect(connect_string)
        self.poller.register(self.pub_sock, zmq.POLLIN)

    def get_update(self):
        data = self.pub_sock.recv_json()
        username, message = data['username'], data['message']
        self.sub_pipe.send_string('{}: {}'.format(username, message))

    def has_message(self):
        events = self.poller.poll()
        return self.pub_sock in events

    def start_main_loop(self):
        self.connect_to_server()
        while True:
            self.get_update()

    def run(self):
        thread = threading.Thread(target=self.start_main_loop)
        thread.daemon = True
        thread.start()

def main():
    server_host = 'localhost'
    chat_port = '5783'
    sub_port = '5784'
    username = sys.argv[1]
    receiver = zmq.Context().instance().socket(zmq.PAIR)
    receiver.bind("inproc://clientchat")
    sender = zmq.Context().instance().socket(zmq.PAIR)
    sender.connect("inproc://clientchat")
    client = ClientChat(username, server_host, chat_port, receiver)
    client.run()

    sub_receiver = zmq.Context().instance().socket(zmq.PAIR)
    sub_receiver.bind("inproc://clientsub")
    sub_sender = zmq.Context().instance().socket(zmq.PAIR)
    sub_sender.connect("inproc://clientsub")
    sub = ClientSub(server_host, sub_port, sub_sender)
    sub.run()
    time.sleep(0.005)

    print ("User "+username+" Connected to the chat server.")

    top_thread = threading.Thread(target=threadrec, args = (sub_receiver,))
    top_thread.daemon = True
    top_thread.start()



    bottom_thread = threading.Thread(target=threadsend, args = (sender,))
    bottom_thread.daemon = True
    bottom_thread.start()

    top_thread.join()
    bottom_thread.join()


if '__main__' == __name__:
    try:
        main()
    except KeyboardInterrupt as e:
        pass
    except:
        raise
