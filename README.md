# tools-car

- sudo apt-get update
- sudo apt-get install libttspico-utils gpsd python-gps mpg123 git-core
- sudo nano /etc/default/gpsd  (DEVICE="/dev/ttyACM0")
- sudo systemctl restart gpsd
- cd
- git clone https://github.com/krotof1a/tools-car
- alsamixer
- cd /lib/systemd/system
- sudo cp /home/chip/tools-car/systemd/* .
- sudo systemctl daemon-reload
- sudo systemctl start ...
- (tests)
- sudo systemctl enable ...
