#!/usr/bin/env python3

from os import environ
from curio import Channel, run
from scibot.core import syncword

if syncword is None:
    raise KeyError('Please set the RRIDBOT_SYNC environment variable')

async def consumer(chan):
    ch = Channel(chan)
    c = await ch.accept(authkey=syncword.encode())
    myset = set()
    while True:
        try:
            msg = await c.recv()
        except (EOFError, ConnectionResetError) as e:  # in the event that the client closes
            print('resetting')
            myset = set()
            c = await ch.accept(authkey=syncword.encode())
            continue
        if msg is None:  # explicit reset
            myset = set()
        else:
            op, uri = msg.split(' ', 1)
            print(op, uri)
            if op == 'add':
                if uri in myset:
                    await c.send(True)
                else:
                    myset.add(uri)
                    await c.send(False)
            elif op == 'del':
                myset.discard(uri)
                await c.send(False)
            else:
                await c.send('ERROR')
        print(myset)

def main():
    chan = ('localhost', 12345)
    run(consumer, chan)

if __name__ == '__main__':
    main()
