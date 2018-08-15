# WiFi sync
A Python3 utility to help sync saved WiFi networks between devices. It finds the SSID and password of all saved networks, and dumps them into a JSON file. It can also restore networks from these files. The actual syncing is delegated to a general file sync application (such as syncthing). It currently has a nmcli backend, but could be expanded to include other Linux, (rooted) Android or Windows backends.

## Usage
Simply run `./wifi-sync update` to sync to the default location (`~/.config/wifi-sync/networks.json`). Use `./wifi-sync -h` for more options.
