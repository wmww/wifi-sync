import sys
import os
import subprocess
import re
import json

default_json_path = '~/.config/wifi-conn-sync/networks.json'

class Run:
    def __init__(self, arg_list, stdin_text=None, raise_on_fail=False):
        print('Running `' + ' '.join(arg_list) + '`...')
        p = subprocess.Popen(arg_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(stdin_text)
        print('  ... Done')
        self.stdout = stdout.decode('utf-8') if stdout != None else ''
        self.stderr = stderr.decode('utf-8') if stderr != None else ''
        self.exit_code = p.returncode
        if raise_on_fail and self.exit_code != 0:
            raise AssertionError(
                '`' + ' '.join(arg_list) + '` exited with code ' + str(self.exit_code) + ':\n' + self.stdout)

class Network:
    def from_json(data):
        if isinstance(data, list):
            return [Network.from_json_single(i) for i in data]
        else:
            return Network.from_json_single(data)

    def from_json_single(data):
        assert 'ssid' in data, 'no SSID in ' + str(data)
        return Network.make(
            data.get('name', data.get('ssid')), # name
            data['ssid'], # ssid
            data.get('pswd_type', 'open'), # pswd_type
            data.get('pswd', None), # pswd
            data.get('autoconnect', True)) # autoconnect

    def make(name, ssid, pswd_type, pswd=None, autoconnect=True):
        assert ssid != None, 'SSID can not be None'
        if name == None:
            name = ssid
        if pswd_type == 'open':
            assert pswd == None, 'Open networks can not have a password'
        elif pswd_type == 'wpa': # or pswd_type == 'wep':
            #assert pswd != None, pswd_type + ' networks must have password'
            pass
        else:
            raise AssertionError('Unknown password type \'' + pswd_type + '\'')
        data = {}
        data['name'] = name
        data['ssid'] = ssid
        data['pswd_type'] = pswd_type
        if pswd != None:
            data['pswd'] = pswd
        if autoconnect == False:
            data['autoconnect'] = False
        return data

    def to_str(data):
        return (
            '| name: ' + data['name'] + '\n' +
            '| SSID: ' + data['ssid'] + '\n' +
            '| type: ' + data['pswd_type'] + '\n' +
            ('' if 'pswd' not in data else '| password: ' + data['pswd'] + '\n') +
            ('' if data.get('autoconnect', True) else '| autoconnect disabled\n'))

class Nmcli:
    bin_path = '/usr/bin/nmcli'

    def is_usable():
        try:
            Run([Nmcli.bin_path, '-v'], raise_on_fail=True)
            return True
        except:
            return False

    def get_network_list():
        out = Run([Nmcli.bin_path, '-f', 'NAME', 'connection'], raise_on_fail=True)
        networks = [i.strip() for i in out.stdout.strip().split('\n')[1:]] # cut off "NAME" header
        return networks

    def parse_single_network(name, data):
        ssids = re.findall('\n802-11-wireless\.ssid:\s*(.*)\n', data)
        psks = re.findall('\n802-11-wireless-security\.psk:\s*(.*)\n', data)
        key_mgmts = re.findall('\n802-11-wireless-security\.key-mgmt:\s*(.*)\n', data)
        autoconnect_nos = re.findall('\n.*\.autoconnect:\s*(no)\n', data)
        assert len(ssids) == 1, 'Could not properly detect SSID'
        assert len(psks) <= 1, 'Found more then one password'
        assert len(key_mgmts) <= 1, 'Found more then one key management'
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
            raise AssertionError('Unknown key management: ' + ' '.join(key_mgmts))
        autoconnect = len(autoconnect_nos) == 0
        return Network.make(name, ssids[0], pswd_type, psk, autoconnect)

    def get_and_parse(names):
        if not isinstance(names, list):
            names = [names]
        out = Run([Nmcli.bin_path, '--show-secrets', 'connection', 'show'] + names, raise_on_fail=True)
        data = out.stdout.split('\n\n')
        assert len(data) == len(names), 'nmcli gave the wrong number of networks'
        networks = []
        for i in range(len(data)):
            try:
                networks.append(Nmcli.parse_single_network(names[i], data[i]))
            except Exception as e:
                print('Error with \'' + names[i] + '\': ' + str(e), file=sys.stderr)
        return networks

    def get_networks(args):
        print('Loading network list...')
        names = Nmcli.get_network_list()
        print('  ... Done')
        try:
            print('Loading network details...')
            networks = Nmcli.get_and_parse(names)
            print('  ... Done')
            return networks
        except Exception as e:
            print('Error: ' + str(e) + ', falling back to individual parsing', file=sys.stderr)
            print('Parsing networks individually...')
            networks = []
            for name in names:
                try:
                    networks += Nmcli.get_and_parse(name)
                except Exception as e:
                    print('Error with \'' + name + '\': ' + str(e), file=sys.stderr)
            print('  ... Done')
            return networks

    def add_network(n):
        args = [Nmcli.bin_path, 'connection', 'add',
            'type', 'wifi',
            'ifname', '*',
            'con-name', n['name'],
            'ssid', n['ssid'],
            'save', 'yes',
            'autoconnect', 'yes' if n.get('autoconnect', True) else 'no']
        pswd_type = n.get('pswd_type', 'NO_PSWD_TYPE_SPECIFIED')
        if pswd_type == 'open':
            pass
        elif pswd_type == 'wpa':
            args += ['802-11-wireless-security.key-mgmt', 'wpa-psk']
            if 'pswd' in n:
                args += ['802-11-wireless-security.psk', n['pswd']]
        elif pswd_type == 'wep':
            raise AssertionError('WEP not yet supported')
        else:
            raise AssertionError('unknown type: ' + pswd_type)
        result = Run(args, raise_on_fail=True)
        print('Network added:\n' + Network.to_str(n))

def get_system_interface():
    if Nmcli.is_usable():
        return Nmcli
    else:
        print('Nmcli failed, no usable system interfaces detected', file=sys.stderr)
        return None

def get_new(old_list, new_list):
    old_dict = {}
    for i in old_list:
        old_dict[i['ssid']] = True
    ret = []
    for i in new_list:
        if i['ssid'] not in old_dict:
            ret.append(i)
    return ret

def json_get_networks(args):
    path = default_json_path
    if args.file != None:
        path = args.file
    print('Loading ' + path + '...')
    contents = '[]'
    try:
        contents = open(path, "r").read()
    except FileNotFoundError:
        print('File ' + path + ' not found, not reading', file=sys.stderr)
    print('  ... Done')
    print('Decoding JSON...')
    ret = json.loads(contents)
    print('  ... Done')
    return ret

def json_save_networks(args, data):
    path = default_json_path
    if args.file != None:
        path = args.file
    if path == default_json_path:
        os.makedirs(os.path.dirname(default_json_path), exist_ok=True)
    print('Saving to ' + path + '...')
    contents = json.dumps(data, indent=2)
    try:
        open(path, "w").write(contents)
    except Exception as e:
        print('Failed to write to ' + path + ' (' + str(e) + ')', file=sys.stderr)
    print('  ... Done')

def import_networks(args, interface):
    j = json_get_networks(args)
    c = interface.get_networks(args)
    n = get_new(c, j)
    if n == []:
        print('No new networks in JSON file')
    else:
        print('Networks to import:\n')
        for i in n:
            print(Network.to_str(i))
        for i in n:
            interface.add_network(i)

def save_networks(args, interface):
    j = json_get_networks(args)
    c = interface.get_networks(args)
    n = get_new(j, c)
    if n == []:
        print('No new networks on system')
    else:
        print('Networks to save:\n')
        for i in n:
            print(Network.to_str(i))
        j += n
        json_save_networks(args, j)

def show_networks(args, interface):
    j = json_get_networks(args)
    c = interface.get_networks(args)
    print('New networks in JSON file:\n')
    for i in get_new(c, j):
        print(Network.to_str(i))
    print('New networks on system:\n')
    for i in get_new(j, c):
        print(Network.to_str(i))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Save and load WiFi networks and passwords; for syncing between devices')
    subparsers = parser.add_subparsers()
    # subparsers.required = True
    # subparsers.dest = 'command'

    parser_load = subparsers.add_parser('import', help='Import a file or directory with WiFi networks')
    parser_load.set_defaults(func=import_networks)
    parser_load.add_argument('-f', '--file', type=str, help='File to import networks from, default is ' + default_json_path)

    parser_load = subparsers.add_parser('save', help='Save WiFi networks to a file or directory')
    parser_load.set_defaults(func=save_networks)
    parser_load.add_argument('-f', '--file', type=str, help='File to save networks to, default is ' + default_json_path)

    parser_load = subparsers.add_parser('show', help='Show WiFi networks loaded from file and detected from system')
    parser_load.set_defaults(func=show_networks)
    parser_load.add_argument('-f', '--file', type=str, help='File to load networks from, default is ' + default_json_path)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        exit(1)

    interface = get_system_interface()
    if interface == None:
        print('No system interface found, exiting', file=sys.stderr)
        exit(1)

    args.func(args, interface)
