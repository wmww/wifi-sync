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
    def __init__(self, name, ssid, psk=None, autoconnect=True):
        assert ssid != None, 'SSID can not be None'
        self.name = name
        self.ssid = ssid
        self.psk = psk
        self.autoconnect = autoconnect

    def __str__(self):
        return (
            '# ' + self.name + '\n' +
            'SSID: ' + self.ssid + '\n' +
            ('' if self.psk == None else 'password: ' + self.psk + '\n') +
            ('' if self.autoconnect else 'don\'t autoconnect\n'))

def nmcli_get_network_list():
    out = Run([nmcli_path, '-f', 'NAME', 'connection'], raise_on_fail=True)
    networks = [i.strip() for i in out.stdout.strip().split('\n')[1:]] # cut off "NAME" header
    return networks

def nmcli_parse_single_network(name, data):
    ssids = re.findall('\n.*\.ssid:\s*(.*)\n', data)
    psks = re.findall('\n.*\.psk:\s*(.*)\n', data)
    autoconnect_nos = re.findall('\n.*\.autoconnect:\s*(no)\n', data)
    assert len(ssids) == 1, 'could not properly detect SSID'
    assert len(psks) <= 1, 'found more then one password'
    autoconnect = len(autoconnect_nos) == 0
    psk = None
    if len(psks) == 1 and psks[0] != '--':
        psk = psks[0]
    return Network(name, ssids[0], psk, autoconnect)

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
            print('error with \'' + names[i] + '\':' + str(e), file=sys.stderr)
    return networks

def nmcli_get_networks():
    names = nmcli_get_network_list()
    try:
        return nmcli_get_and_parse(names)
    except Exception as e:
        print('error:' + str(e) + ', falling back to parsing networks individually', file=sys.stderr)
        networks = []
        for name in names:
            try:
                networks.append(nmcli_get_and_parse(name))
            except Exception as e:
                print('error with \'' + name + '\':' + str(e), file=sys.stderr)
        return networks

if __name__ == '__main__':
    print('\n'.join([str(i) for i in nmcli_get_networks()]))
