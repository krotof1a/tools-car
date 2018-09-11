#! /usr/bin/python
 
import os
from gps import *
from time import *
from haversine import haversine
import time
import threading
import zipfile

#setting the constants
MAINREFRESH=1   # Refresh rate of proximity radars analysis in seconds
PROXYREFRESH=60 # Refresh rate of the proximity list of POI is seconds
DBFILE = '/home/chip/rad_txt-iGO-EUR.zip'
POIFILE = 'SpeedCam.txt'
WARNINGDISTANCEREF = 0.4 # Ref warning distance in km for low speed (under 60km/h)
WARNINGDISTANCEMULTIPLICATORMEDIUM = 2 # Multiplicator of warning distance for medium speed (under 90km/h)
WARNINGDISTANCEMULTIPLICATORHIGH   = 3 # Multiplicator of warning distance for high  speed (under 130km/h)
WARNINGDISTANCEMULTIPLICATOROVER   = 5 # Multiplicator of warning distance for over  speed (above 130km/h)
POSIMPRECISION = 0.05 # Imprecision in real precise position

#setting the global variables
gpsd = None 
poi  = []
proxyPoi = []
PROXYDISTANCE=3*PROXYREFRESH/60 # Max distance covered at 180km/h between 2 refreshes
currentMode = 0 # 0 = no GPS, 1 = GPS, 2 = light warning, 3 = heavy warning, 4 = in limited section

class Alerting(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.current_value = None
    self.running = True #setting the thread running to true
 
  def run(self):
    global currentMode
    while self.running:
	time.sleep(1)

class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsd #bring it in scope
    gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsd
    while self.running:
      gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
 
class ProxyPOISelector(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsd, poi, proxyPoi, PROXYREFRESH, PROXYDISTANCE, currentMode
    while self.running:
		if not currentMode == 0:
			if len(poi) > 0:
				print 'Start proximity radar selection'
				localPos = (gpsd.fix.latitude, gpsd.fix.longitude)
				proxyPoi = []
				for counter, radar in enumerate(poi):
					radarPos = (float(radar[1]), float(radar[0]))
					radarDis = haversine(localPos,radarPos)
					if radarDis <= PROXYDISTANCE:
						proxyPoi.insert(0,(radar[0], radar[1], radar[2], radar[3], radar[4], radar[5], radarDis))
				print 'End proximity radar selection'
				for i in range(PROXYREFRESH): # Used to wait but not blocking for Thread termination
					if self.running:
						time.sleep(1)
					else:
						break
			else:
				time.sleep(1)
		else:
			time.sleep(1)

if __name__ == '__main__':
  # Read radars list from archive
  zipFile = zipfile.ZipFile(DBFILE, 'r')
  with zipFile.open(POIFILE) as f:
      for line in f:
           radar = line.strip('\n').strip('\r').split(",")
	   # Format is X,Y,TYPE,SPEED,DIRTYPE,DIRECTION
	   if not radar[0]=='X': # discard header of file
	   	 poi.insert(0,(radar[0], radar[1], radar[2], radar[3], radar[4], radar[5]))
  # Create helper's threads
  gpsp = GpsPoller()
  poip = ProxyPOISelector()
  alert = Alerting()
  # Start everything
  try:
    gpsp.start()
    poip.start()
    alert.start()

    while True:
      os.system('clear')
      print
      print ' GPS reading'
      print '----------------------------------------'
      print 'latitude     ' , gpsd.fix.latitude
      print 'longitude    ' , gpsd.fix.longitude
      print 'speed (km/h) ' , gpsd.fix.speed*3.6
      print 'track        ' , gpsd.fix.track
      print
      print 'Records in DB: '+str(len(poi))
      print 'Current mode : ',str(currentMode)

      if not (gpsd.fix.latitude == 0 and gpsd.fix.longitude == 0):
	currentMode=1
        localPos = (gpsd.fix.latitude, gpsd.fix.longitude)
        # Set warning distance according to current speed
        if gpsd.fix.speed*3.6 <= 60:
		WARNINGDISTANCE=WARNINGDISTANCEREF
        elif gpsd.fix.speed*3.6 <= 90:
		WARNINGDISTANCE=WARNINGDISTANCEREF*WARNINGDISTANCEMULTIPLICATORMEDIUM
        elif gpsd.fix.speed*3.6 <= 130:
		WARNINGDISTANCE=WARNINGDISTANCEREF*WARNINGDISTANCEMULTIPLICATORHIGH
        else:
		WARNINGDISTANCE=WARNINGDISTANCEREF*WARNINGDISTANCEMULTIPLICATOROVER
        # Check proximity radars to know if we should warn
	updateStatus=0
        for counter, radar in enumerate(proxyPoi):
      	        print 'Proximity radar '+str(counter)
		radarPos = (float(radar[1]), float(radar[0]))
		radarDis = haversine(localPos,radarPos)
		if radarDis <= radar[6] + POSIMPRECISION: # Getting closer from the radar
		   if radarDis <= WARNINGDISTANCE: # We are under warning distance
			if radar[2] == '1' or radar[2] == '69': # Warn only for RF and RFR
				print str(radar)
				lowlim = (float(radar[5])-45)%360
				hghlim = (float(radar[5])+45)%360
				if radar[4] == '0' or (radar[4] == '1' and gpsd.fix.track > lowlim and gpsd.fix.track < hghlim) or radar[4] == '2':
					if float(radar[3])==0 or (gpsd.fix.speed*3.6)>radar[3]:
						print '- WARNING'
						currentMode=3
						updateStatus=1
					else:
						print '- LIGHT WARNING'
						currentMode=2
						updateStatus=1
				else:
					print '- Radar is not in the driving direction'
			else:
				print '- Radar is not a RF or RFR  one'
		   else:
			print '- Radar is too far'
		else:
		   print '- Radar distance is increasing'
		# update of radar distance
		proxyPoi[counter]=(radar[0], radar[1], radar[2], radar[3], radar[4], radar[5], radarDis)
	# update status
	if updateStatus==0 and currentMode>1:
		currentMode=1
      else:
	currentMode=0
      time.sleep(MAINREFRESH)
 
  except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    print "\nKilling Threads..."
    gpsp.running  = False
    poip.running  = False
    alert.running = False
    gpsp.join() # wait for the thread to finish what it's doing
    poip.join()
    alert.join()
    time.sleep(1)
  print "Done.\nExiting."

