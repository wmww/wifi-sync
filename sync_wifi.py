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

def parse_from_nmcli(name):
    out = Run([nmcli_path, '--show-secrets', 'connection', 'show', name], raise_on_fail=True)
    ssids = re.findall('\n.*\.ssid:\s*(.*)\n', out.stdout)
    psks = re.findall('\n.*\.psk:\s*(.*)\n', out.stdout)
    autoconnect_nos = re.findall('\n.*\.autoconnect:\s*(no)\n', out.stdout)
    assert len(ssids) == 1, 'could not properly detect SSID'
    assert len(psks) <= 1, 'found more then one password'
    autoconnect = len(autoconnect_nos) == 0
    psk = None
    if len(psks) == 1 and psks[0] != '--':
        psk = psks[0]
    return Network(name, ssids[0], psk, autoconnect)

def get_all_from_nmcli():
    names = nmcli_get_network_list()
    networks = []
    for name in names:
        try:
            networks.append(parse_from_nmcli(name))
        except Exception as e:
            print('error with \'' + name + '\': ' + str(e))
    return networks

if __name__ == '__main__':
    print('\n'.join([str(i) for i in get_all_from_nmcli()]))
