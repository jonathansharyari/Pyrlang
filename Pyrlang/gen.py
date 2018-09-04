""" A helper module to assist with gen:call-style message parsing and replying.
    A generic incoming message looks like ``{$gen_call, {From, Ref}, Message}``.
"""

from Pyrlang import Term


class GenBase:
    """ Base class for Gen messages, do not use directly. See
        ``GenIncomingMessage`` and ``GenIncomingCall``.
    """
    def __init__(self, sender, ref, node_name: str):
        self.node_name_ = node_name
        self.sender_ = sender
        """ Where to send replies to. """
        self.ref_ = ref
        """ An unique ref generated by the caller. 
            A ``term.Reference`` object. 
        """

    def reply(self, local_pid, result):
        """ Reply with a gen:call result
        """
        from Pyrlang.node import Node
        n = Node.all_nodes[self.node_name_]
        n.send(sender=local_pid,
               receiver=self.sender_,
               message=(self.ref_, result))

    def reply_exit(self, local_pid, reason):
        """ Reply to remote gen:call with EXIT message which causes reason to be
            re-raised as exit() on the caller side
            NOTE: The gen:call caller attempts to monitor the target first. If
                the monitor attempt fails, the exit here won't work
        """
        from Pyrlang.node import Node

        reply = ('monitor_p_exit', local_pid, self.sender_, self.ref_, reason)
        n = Node.all_nodes[self.node_name_]
        n.dist_command(receiver_node=self.sender_.node_.text_, message=reply)


class GenIncomingMessage(GenBase):
    """ A helper class which contains elements from a generic incoming
        ``gen_server`` message.
        For those situations when gen message is not a call, or is an incoming
        ``gen_server`` call.
    """
    def __init__(self, sender, ref, message, node_name: str):
        GenBase.__init__(self, sender=sender, ref=ref, node_name=node_name)
        self.message_ = message
        """ The last part of the incoming message, the payload. """

    def __str__(self):
        return "GenIncomingMessage(" + str(self.message_) + ")"


class GenIncomingCall(GenBase):
    """ A helper class which contains elements from the incoming
        ``gen:call`` RPC call message.
    """

    def __init__(self, mod, fun, args, group_leader, sender, ref,
                 node_name: str):

        GenBase.__init__(self, sender=sender, ref=ref, node_name=node_name)
        self.mod_ = mod
        """ Module name as atom. """

        self.fun_ = fun
        """ Function name as atom. """

        self.args_ = args
        """ Call arguments as a ``term.List`` object. """

        self.group_leader_ = group_leader
        """ Remote group leader pid, comes in as a part of message. """

    def get_args(self):
        """ Returns parsed args for the RPC call. """
        if isinstance(self.args_, list):
            return self.args_
        return self.args_.elements_

    def get_mod_str(self):
        """ Returns module name as a string. """
        return self.mod_.text_

    def get_fun_str(self):
        """ Returns function name as a string. """
        return self.fun_.text_


def parse_gen_call(msg):
    """ Determine if msg is a gen:call message

        :param msg: An Erlang tuple hopefully starting with a '$gen_call'
        :return: str with error if msg wasn't a call message, otherwise
            constructs and returns a ``GenIncomingCall`` object.
    """
    # Incoming {$gen_call, {From, Ref}, {call, Mod, Fun, Args}}
    if type(msg) != tuple:  # ignore all non-tuple messages
        return "Only {tuple} messages allowed"

    # ignore tuples with non-atom 1st, ignore non-gen_call mesages
    if not isinstance(msg[0], Term.Atom) or msg[0].text_ != '$gen_call':
        return "Only {$gen_call, _, _} messages allowed"

    (_, _sender_mref, _call_mfa_gl) = msg
    (msender, mref) = _sender_mref

    if len(_call_mfa_gl) != 5:
        return "Expecting a 5-tuple (with a 'call' atom)"
        # TODO: Maybe also check first element to be an atom 'call'

    # A gen_call call tuple has 5 elements, otherwise see below
    (call, m, f, args, group_leader) = _call_mfa_gl

    if not isinstance(m, Term.Atom):
        return "Module must be an atom: %s" % str(m)

    if not isinstance(f, Term.Atom):
        return "Function must be an atom: %s" % str(f)

    return GenIncomingCall(mod=m,
                           fun=f,
                           args=args,
                           group_leader=group_leader,
                           sender=msender,  # pid of the sender
                           ref=mref  # reference used in response
                           )


def parse_gen_message(msg, node_name: str):
    """ Might be an 'is_auth' request which is not a call

        :return: string on error, otherwise a ``GenIncomingMessage`` object
    """
    # Incoming {$gen_call, {From, Ref}, Message}
    if type(msg) != tuple:  # ignore all non-tuple messages
        return "Only {tuple} messages allowed"

    # ignore tuples with non-atom 1st, ignore non-gen_call mesages
    if not isinstance(msg[0], Term.Atom) or msg[0].text_ != '$gen_call':
        return "Only {$gen_call, _, _} messages allowed"

    (_, _sender_mref, gcmsg) = msg
    (msender, mref) = _sender_mref

    return GenIncomingMessage(sender=msender,
                              ref=mref,
                              message=gcmsg,
                              node_name=node_name)


__all__ = ['GenIncomingCall', 'GenIncomingMessage',
           'parse_gen_call', 'parse_gen_message']
