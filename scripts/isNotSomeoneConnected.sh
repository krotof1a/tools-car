#!/bin/sh

LEASE_END_TIME=`cat /var/lib/misc/dnsmasq.leases | tail -1 | awk '{ print $1 }'`
BOOT_TIME=`cat /proc/stat | grep btime | awk '{ print $2 }'`
if [ "$LEASE_END_TIME" == "" ]
then
	exit 0
fi
LEASE_TIME=`expr $LEASE_END_TIME - 43200`
if [ $LEASE_TIME -gt $BOOT_TIME ]
then
	exit 1
else
	exit 0
fi

