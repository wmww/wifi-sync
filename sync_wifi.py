import sys
import subprocess
import re

nmcli_path = '/usr/bin/nmcli'

class Run:
    def __init__(self, arg_list, stdin_text=None, raise_on_fail=False):
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(stdin_text)
        self.stdout = stdout.decode('utf-8') if stdout != None else ''
        self.stderr = stderr.decode('utf-8') if stderr != None else ''
        self.exit_code = p.returncode
        if raise_on_fail and self.exit_code != 0:
            raise AssertionError(
                '`' + ' '.join(arg_list) + '` exited with code ' + str(self.exit_code) + ':\n' + self.stdout)

class Network:
    def __init__(self, name, ssid, pswd_type, pswd=None, autoconnect=True):
        assert ssid != None, 'SSID can not be None'
        if pswd_type == 'open':
            assert pswd == None, 'open networks can not have a password'
        elif pswd_type == 'wpa' or pswd_type == 'wep':
            #assert pswd != None, pswd_type + ' networks must have password'
            pass
        else:
            raise AssertionError('unknown password type \'' + pswd_type + '\'')
        self.name = name
        self.pswd_type = pswd_type
        self.ssid = ssid
        self.pswd = pswd
        self.autoconnect = autoconnect

    def __str__(self):
        return (
            '| name: ' + self.name + '\n' +
            '| SSID: ' + self.ssid + '\n' +
            '| type: ' + self.pswd_type + '\n' +
            ('' if self.pswd == None else '| password: ' + self.pswd + '\n') +
            ('' if self.autoconnect else '| autoconnect disabled\n'))

def nmcli_get_network_list():
    out = Run([nmcli_path, '-f', 'NAME', 'connection'], raise_on_fail=True)
    networks = [i.strip() for i in out.stdout.strip().split('\n')[1:]] # cut off "NAME" header
    return networks

def nmcli_parse_single_network(name, data):
    ssids = re.findall('\n802-11-wireless\.ssid:\s*(.*)\n', data)
    psks = re.findall('\n802-11-wireless-security\.psk:\s*(.*)\n', data)
    key_mgmts = re.findall('\n802-11-wireless-security\.key-mgmt:\s*(.*)\n', data)
    autoconnect_nos = re.findall('\n.*\.autoconnect:\s*(no)\n', data)
    assert len(ssids) == 1, 'could not properly detect SSID'
    assert len(psks) <= 1, 'found more then one password'
    assert len(key_mgmts) <= 1, 'found more then one key management'
    psk = None
    if len(psks) == 1 and psks[0] != '--':
        psk = psks[0]
    pswd_type = None
    if len(key_mgmts) == 0:
        pswd_type = 'open'
    elif key_mgmts[0] == 'none':
        raise AssertionError('WEP isn\'t properly supported yet')
        pswd_type = 'wep'
    elif key_mgmts[0] == 'wpa-psk':
        pswd_type = 'wpa'
    else:
        raise AssertionError('unknown key management: ' + ' '.join(key_mgmts))
    autoconnect = len(autoconnect_nos) == 0
    return Network(name, ssids[0], pswd_type, psk, autoconnect)

def nmcli_get_and_parse(names):
    if not isinstance(names, list):
        names = [names]
    out = Run([nmcli_path, '--show-secrets', 'connection', 'show'] + names, raise_on_fail=True)
    data = out.stdout.split('\n\n')
    assert len(data) == len(names), 'nmcli gave the wrong number of networks'
    networks = []
    for i in range(len(data)):
        try:
            networks.append(nmcli_parse_single_network(names[i], data[i]))
        except Exception as e:
            print('error with \'' + names[i] + '\': ' + str(e), file=sys.stderr)
    return networks

def nmcli_get_networks():
    print('loading network list...')
    names = nmcli_get_network_list()
    print('...done')
    try:
        print('loading network details...')
        networks = nmcli_get_and_parse(names)
        print('...done')
        return networks
    except Exception as e:
        print('error: ' + str(e) + ', falling back to parsing networks individually', file=sys.stderr)
        networks = []
        for name in names:
            try:
                networks += nmcli_get_and_parse(name)
            except Exception as e:
                print('error with \'' + name + '\': ' + str(e), file=sys.stderr)
        print('...done')
        return networks

def nmcli_add_network(n):
    args = [nmcli_path, 'connection', 'add',
        'type', 'wifi',
        'ifname', '*',
        'con-name', n.name,
        'ssid', n.ssid,
        'save', 'yes',
        'autoconnect', 'yes' if n.autoconnect else 'no']
    if n.pswd_type == 'open':
        pass
    elif n.pswd_type == 'wpa':
        args += ['802-11-wireless-security.key-mgmt', 'wpa-psk']
        if n.pswd != None:
            args += ['802-11-wireless-security.psk', n.pswd]
    elif n.pswd_type == 'wep':
        raise AssertionError('WEP not yet supported')
    else:
        raise AssertionError('unknown type: ' + n.pswd_type)
    result = Run(args, raise_on_fail=True)
    print('network added:\n' + str(n))

def load_networks(args):
    print('load_networks()')
    print('    path: ' + args.path)
    #n = nmcli_get_networks()
    #print('parsed ' + str(len(n)) + ' networks\n')
    #print('\n'.join([str(i) for i in n]))

def save_networks(args):
    print('save_networks()')
    print('    path: ' + args.path)
    print('    split: ' + str(args.split))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Save and load WiFi networks and passwords; for syncing between devices')
    subparsers = parser.add_subparsers()
    # subparsers.required = True
    # subparsers.dest = 'command'

    parser_load = subparsers.add_parser('load', help='load a file or directory with WiFi networks')
    parser_load.set_defaults(func=load_networks)
    parser_load.add_argument('path', type=str, help='file or directory')

    parser_load = subparsers.add_parser('save', help='save WiFi networks to a file or directory')
    parser_load.set_defaults(func=save_networks)
    parser_load.add_argument('path', type=str, help='file or directory')
    parser_load.add_argument('-s', '--split', action='store_true', help='split networks into different files')

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        exit(1)

    args.func(args)
