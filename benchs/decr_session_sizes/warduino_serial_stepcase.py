import json
from os import read
from serial.serialposix import Serial
import math

import serial
import serial.tools.list_ports
import time
import sys

def sum_hexs(hexs):
    sum = 0
    for h in hexs:
       x = h if isinstance(h, int) else int( h[2:], 16)
       sum += x

    return hex(sum)

def bp_addr_helper(offset, code_addr):
    bp_addr = sum_hexs([offset, code_addr])  # remove '0x'
    amount_chars = math.floor(len(bp_addr[2:]) / 2)
    if amount_chars % 2 != 0:
        print("WARNING: breakpoint address is not even addr")
        print(
            f"offset {offset} code_addr {code_addr} chars {amount_chars} calculated addr: {bp_addr}")
    else:
        pass

    _hex = hex(amount_chars)
    if int(_hex[2:], 16) < 16:
        _hex = '0x0' + _hex[2:]
    content = '06' + _hex[2:] + bp_addr[2:] + '\n'
    return content.upper()

def await_output(s: serial.Serial, target: str):
    target = target.encode('utf-8')
    curpos: int = 0
    while True:
        x = s.read()
        print(x.decode('utf-8', 'replace'), end="", file=sys.stderr)
        x = x[0]
        if x == b'\r'[0]:
            continue
        if x == target[curpos]:
            curpos += 1
            if curpos == len(target):
                curpos = 0
                return
        else:
            curpos = 0

def read_content(s: serial.Serial, c: bytes = b'\n'):
    r = s.read_until(c)
    return r

# def step(s: serial.Serial):
#     s.write('04'.encode())
#     content = read_content(s)
#     step_ack = content.decode()
#     assert 'STEP' in step_ack

def ask_debug_session():
    #ask dump
    print('asking for dump')
    serial.write('10\n'.encode())
    content = read_content(serial)
    dump_ack = content.decode()
    assert 'DUMP!' in dump_ack, f'GOT {dump_ack}'

    print('waiting for dump content')
    content = read_content(serial)
    dump = content.decode()
    assert 'start' in dump

    ddump = json.loads(dump)
    l = len(ddump['callstack'])
    assert  l <= callstack_size, f'callstack size {callstack_size} > {l}'

    #ask locals
    print('asking for locals')
    serial.write('11\n'.encode())
    content = read_content(serial)
    locs_ack = content.decode()
    assert 'DUMP LOCALS' in locs_ack

    content = read_content(serial)
    content2 = read_content(serial)
    locs = content.decode()
    content2 = content2.decode()
    assert 'count' in locs, f'got {locs}'
    assert len(content2) == 2, f'got {content2} len={len(content2)}'
    return dump,locs

if __name__ == "__main__":
    port = None
    ports = [port.device for port in serial.tools.list_ports.comports()]
    if not ports:
        print("Device not found!")
        exit(1)
    elif len(ports) > 1:
        print("More than one serial port found!")
        for i in range(len(ports)):
            print(f"{i}: {ports[i]}")
        port = ports[int(input(f"Select port [0-{len(ports) - 1}]:"))]
    else:
        port = ports[0]
    print(f"using {port}", file=sys.stderr)

    with serial.Serial(port, 115200) as serial:

        arg= int(sys.argv[1])
        print(f"argument {arg}")
        callstack_size = 2 * (arg + 1) + 2

        print('reading offset')
        await_output(serial, "OFFSET\n")
        # content = read_content(serial)
        # content = content.decode()
        # assert 'OFFSET' in content, f'got {content}'


        content = read_content(serial)
        content = content.decode()
        assert '!' in content

        offset = content[:-3]
        print(f'decoded offset {offset}')
        int(offset, 16)
        addr = '0x61'

        #add breakpoint
        print('adding breakpoint')
        interrupt = bp_addr_helper(offset, addr)
        serial.write(interrupt.encode())
        content = read_content(serial)
        bp_added = content.decode()
        assert 'BP' in bp_added, f'Got {bp_added}'


        #wait for at bp
        print('waiting for At breakpoint')
        # a = hex(int(offset, 16) + int(addr, 16))[2:]
        content = read_content(serial)
        at_bp = content.decode()
        print(f"at_bp_content {at_bp}")
        assert 'AT' in at_bp

        outputfile = 'decr_warduino_debugsession_sizes_step.txt'
        f = open(outputfile , "a")
        for i in range(11):
            if i != 0:
                #step
                print(f"stepping #{i}")
                serial.write('04\n'.encode())
                # await_output(serial, 'STEP!')
                content = read_content(serial)
                step_ack = content.decode()
                assert 'STEP' in step_ack, f'got {step_ack}'

            dump, locs = ask_debug_session()
            f.write(f'arg={arg},callstack={callstack_size},session_size={len(dump) + len(locs)}\n')
        f.close()

        #ask dump
        # print('asking for dump')
        # serial.write('10\n'.encode())
        # content = read_content(serial)
        # dump_ack = content.decode()
        # assert 'DUMP!' in dump_ack, f'GOT {dump_ack}'

        # print('waiting for dump content')
        # content = read_content(serial)
        # dump = content.decode()
        # assert 'start' in dump

        # ddump = json.loads(dump)
        # l = len(ddump['callstack'])
        # assert  l == callstack_size, f'callstack size {callstack_size} != {l}'

        # #ask locals
        # print('asking for locals')
        # serial.write('11\n'.encode())
        # content = read_content(serial)
        # locs_ack = content.decode()
        # assert 'DUMP LOCALS' in locs_ack

        # content = read_content(serial)
        # locs = content.decode()
        # assert 'count' in locs, f'got {locs}'
