import subprocess

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

def nmcli_get_network_list():
    out = Run([nmcli_path, '-f', 'NAME', 'connection'], raise_on_fail=True)
    networks = out.stdout.split()[1:] # cut off "NAME" header
    return networks

def parse_from_nmcli():
    return None

if __name__ == '__main__':
    print(nmcli_get_network_list())
