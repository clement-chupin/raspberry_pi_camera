

sudo apt update -y && sudo apt upgrade -y
sudo apt install -y python3-picamera2 python3-opencv libcamera-apps python3-rpi.gpio ffmpeg && pip3 install flask numpy



sudo mv raspcam.service /etc/systemd/system/raspcam.service
sudo systemctl daemon-reload
sudo systemctl enable raspcam.service
sudo systemctl start raspcam.service
