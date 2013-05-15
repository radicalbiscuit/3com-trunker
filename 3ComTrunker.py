#!/usr/bin/env python
import re
import telnetlib

from argparse import ArgumentParser
from sys import version_info

if version_info < (2, 7):
    print('This script requires Python 2.7 or higher due to argparse.')
    quit()

def print_nonewline(data):
    if version_info < (3, 0):
        print(data),
    else:
        # eval() is used so the Python 3 print function syntax doesn't
        # throw an exception in Python 2
        eval("print('{0}', end=' ')".format(data))

####################################################
###            Defaults and Constants            ###
####################################################
# Default values for the optional arguments
default_args = {
        'username': 'admin',
        'password': '',
        'tcp_port': 23,
        'port_ranges': '1-24',
        'native_vlan': 1,
}

# All of the following are lists of regexes
USERNAME_PROMPTS = [re.compile('^Username:$', re.M)]
PASSWORD_PROMPTS = [re.compile('^Password:$', re.M)]
SHELL_PROMPTS = [re.compile('^<.*?>$', re.M), re.compile('^\[.*?\]$', re.M)]

####################################################
###                    Setup                     ###
####################################################
desc = 'A script to trunk and permit a vlan on all ports of a 3com switch.'
parser = ArgumentParser(description=desc)

parser.add_argument('-i',
                    '--ip_address',
                    help='The IP address of the switch',
                    required=True)
parser.add_argument('-v',
                    '--voice_vlan',
                    help='The voice vlan ID',
                    required=True,
                    type=int)
parser.add_argument('-u',
                    '--username',
                    help='The username to use when logging in to the switch',
                    default=default_args['username'])
parser.add_argument('-p',
                    '--password',
                    help='The password to use when logging in to the swtich',
                    default=default_args['password'])
parser.add_argument('-t',
                    '--tcp_port',
                    help='The TCP port to use when initiating connection',
                    default=default_args['tcp_port'],
                    type=int)
parser.add_argument('-r',
                    '--port_ranges',
                    help=('The ranges of switch ports on which the '
                          'actions should be performed, separated by '
                          'comma (i.e. "1-24", "1,3,14-22", "15"'),
                    default=default_args['port_ranges'])
parser.add_argument('-n',
                    '--native_vlan',
                    help='The native vlan ID',
                    default=default_args['native_vlan'],
                    type=int)

args = vars(parser.parse_args())

range_re = re.compile('^(\d+)-(\d+)$') # A regex describing how a range looks
ports = []
for r in args['port_ranges'].split(','):
    try:
        if range_re.match(r): # If the current element is a range...
            start, end = map(int, range_re.search(r).groups())
            ports.extend(range(start, end + 1))
        else: # /Should/ be a single port number
            ports.append(int(r))
    except ValueError:
        print('invalid port range item given: {0}\n'.format(r))
        parser.parse_args(['-r'])

####################################################
###                 Main Section                 ###
####################################################
print('Logging on to %s:%d' % (args['ip_address'], args['tcp_port']))
telnet = telnetlib.Telnet(args['ip_address'], args['tcp_port'])
print('Connected')

def expect_or_die(expect_list, timeout=5):
    response = telnet.expect(expect_list, timeout)
    if response[0] < 0:
        raise Exception(
                ("Couldn't read the expected text, "
                 'got this instead:\n{0}').format(response[2].__repr__()))
    return response

try:
    expect_or_die(USERNAME_PROMPTS)
    
    print('Entering username')
    telnet.write(args['username'] + '\n')
    
    expect_or_die(PASSWORD_PROMPTS)
    print('Entering password')
    telnet.write(args['password'] + '\n')
    
    expect_or_die(SHELL_PROMPTS)
    telnet.write('system-view\n')
    expect_or_die(SHELL_PROMPTS)
    
    print_nonewline('Programming the ports: ')
    for port in ports:
        port_prompt = '^\[.*?-GigabitEthernet1/0/{0}\]$'.format(port)
        port_prompt = [re.compile(port_prompt, re.M)]
        
        # Here are where the commands are sent
        telnet.write('int gig 1/0/{0}\n'.format(port))
        expect_or_die(port_prompt)
        telnet.write('port link-type trunk\n')
        expect_or_die(port_prompt)
        vlans = 'port trunk permit vlan {0} {1}\n'.format(args['native_vlan'],
                                                          args['voice_vlan'])
        telnet.write(vlans)
        expect_or_die(['.*?\sPlease wait\.\.\. Done\.'])
        expect_or_die(port_prompt)
        print_nonewline(port)
except:
    telnet.close()
    raise

print('\nDone')
telnet.close()
