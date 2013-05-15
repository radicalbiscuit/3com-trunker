#!/usr/bin/env python
import re
import telnetlib

from argparse import ArgumentParser

####################################################
###            Defaults and Constants            ###
####################################################
# Default values for the optional arguments
default_args = {
        'username': 'admin',
        'password': '',
        'tcp_port': 23,
        'port_ranges': '1-24',
}

# All of the following are lists of regexes
USERNAME_PROMPTS = ['^Username:']
PASSWORD_PROMPTS = ['^Password:']
SHELL_PROMPTS = ['^<.*?>$', '^[.*?]$']

####################################################
###                    Setup                     ###
####################################################
desc = 'A script to trunk and permit a vlan on all ports of a 3com switch.'
parser = ArgumentParser(description=desc)

parser.add_argument('-i',
                    '--ip_address',
                    help='The IP address of the switch',
                    required=True)
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
    except ValueError, e:
        print('invalid port range item given: {0}\n'.format(r))
        parser.parse_args(['-r'])

####################################################
###                 Main Section                 ###
####################################################
print('Logging on to %s:%d' % (args['destination'], args['tcp_port']))
telnet = telnetlib.Telnet(args['ip_address'], args['tcp_port'])

telnet.expect(USERNAME_PROMPTS)
print('Entering username')
telnet.write(args['username'] + '\n')

telnet.expect(PASSWORD_PROMPTS)
print('Entering password')
telnet.write(args['password'] + '\n')

telnet.expect(SHELL_PROMPTS)
telnet.write('system-view\n')
response = telnet.expect(SHELL_PROMPTS)
assert (response[0] == 1), 'The shell failed to switch to system-view mode.'

print('Programming the ports', end='')
for port in xrange(1, args['number_of_ports'] + 1):
    port_prompt = '^[.*?-GigabitEthernet1/0/{0}]$'.format(port)

    telnet.write('int gig 1/0/{0}\n'.format(port))
    telnet.expect(port_prompt)
    telnet.write('port link-type trunk')
    telnet.expect(port_prompt)
    telnet.write('port trunk permit vlan 1 10')
    telnet.read_until(' Please wait... Done.')
    telnet.expect(port_prompt)
    print('.', end='')

print('\nDone')
telnet.close()
