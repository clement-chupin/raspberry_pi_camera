sudo nmcli device wifi hotspot ssid RaspCam_55 password 12345678
sudo nmcli connection modify "Hotspot" connection.autoconnect-priority -1
nmcli -f NAME,UUID,AUTOCONNECT,AUTOCONNECT-PRIORITY c

