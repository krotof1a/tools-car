#!/bin/sh

while true
do
	REGB9H=`i2cget -f -y 0 0x34 0xb9`  # Read AXP209 register B9H
	PERC_CHG=$(($REGB9H))  # convert to decimal
	#echo "$PERC_CHG"
	if [ $PERC_CHG -le 90 ]
	then
		echo "Stopping"
		shutdown -h now
	fi
	sleep 60
done


