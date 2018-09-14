#!/bin/sh

# Wait for network availability
cur=`ping -c 1 github.com > /dev/zero 2>&1 ; echo $?`
while [ $cur -ne 0 ]
do
	echo "Wait for network !"
	sleep 1
	cur=`ping -c 1 github.com > /dev/zero 2>&1 ; echo $?`
done

# Update chip directory from GitHub
cd /home/chip/tools-car
git pull

exit 0
