sudo apt update -y && sudo apt upgrade -y
sudo apt install -y python3-picamera2 python3-opencv libcamera-apps python3-rpi.gpio ffmpeg && pip3 install flask numpy

sudo nmcli device wifi hotspot ssid RaspCam_55 password 12345678
mkdir template
mv index.html template/index.html
sudo mv raspcam.service /etc/systemd/system/raspcam.service
sudo systemctl daemon-reload
sudo systemctl enable raspcam.service
sudo systemctl start raspcam.service



# see the camera resolution options :
rpicam-vid

# see the wifi configs :
nmcli -f NAME,UUID,AUTOCONNECT,AUTOCONNECT-PRIORITY c

# change the wifi connection to wifi acces point :
sudo nmcli connection modify "Hotspot" connection.autoconnect-priority 1
