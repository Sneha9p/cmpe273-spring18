import zmq


class Server(object):

    def __init__(self, chat_interface, ch_p, pub_interface, sub_port):
        self.chat_interface = chat_interface
        self.ch_p = ch_p
        self.pub_interface = pub_interface
        self.sub_port = sub_port
        self.context = zmq.Context()
        self.ch_socket = None
        self.pub_sock = None

    def bind_ports(self):
        self.ch_socket = self.context.socket(zmq.REP)
        chat_bind_string = 'tcp://{}:{}'.format(
            self.chat_interface, self.ch_p)
        self.ch_socket.bind(chat_bind_string)

        self.pub_sock = self.context.socket(zmq.PUB)
        sub_bind_string = 'tcp://{}:{}'.format(
            self.pub_interface, self.sub_port)
        self.pub_sock.bind(sub_bind_string)

    def get_message_with_username(self):
        data = self.ch_socket.recv_json()
        print(data)
        username = data['username']
        message = data['message']
        return [username, message]

    def update_subs(self, username, message):
        data = {
            'username' : username,
            'message' : message,
        }
        self.ch_socket.send(b'\x00')
        self.pub_sock.send_json(data)

    def start_main_loop(self):
        self.bind_ports()
        while True:
            username, message = self.get_message_with_username()
            self.update_subs(username, message)


if '__main__' == __name__:
    try:
        ch_p = 5783
        sub_port = 5784
        server = Server('*', ch_p, '*', sub_port)
        server.start_main_loop()
    except KeyboardInterrupt:
        pass
