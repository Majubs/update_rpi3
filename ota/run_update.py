#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 19:31:29 2020

@author: majubs
"""
import sys, json, logging
from pi3_device import Device
from manifest_handler import Manifest
# from threading import Timer
from time import sleep

# num = 0

def read_last_conf():
	conf = ''
	try:
		with open('config.json', 'r') as infile:
			conf = json.load(infile)
	# Do something with the file
	except IOError:
		logging.debug("Configuration file not found. Cannot access platform.")
	
	return conf

def periodic_run(D, M, status):
# 	global num
# 	num = num+1
	
	# check if its the first start of a new FW
	if D.check_first_start():
		logging.debug("Starting a new FW")
		if D.check_start():
			logging.debug("New version: ", D.version)
			D.send_device_status([D.get_device_status()])
			D.send_message("Update correct")
		else:
			logging.debug("New FW did not start correctly")
			D.send_exception("Update incorrect")
			D.rollback()
		return
	else:
		logging.debug("Starting OTA process")
	
	status.append(D.get_device_status())
	ret = M.get_manifest()
	if ret == 1:
		# each time a update arrives, get network information
		net_info = D.get_network_info()
		D.send_message(net_info)
		status.append(D.get_device_status())
		D.send_message("Manifest received")
		M.parse_manifest(D)
		if M.valid:
# 			sleep(2)
			status.append(D.get_device_status())
			D.send_message("Manifest correct")
			#if M.apply_manifest(D, status):
			#	logging.debug("Update finished!")
			#	status.append(D.get_device_status())
			#	D.send_message("Update done")
			#   # send status before restart
			#	D.send_device_status(status)
			#	D.restart()
			if M.download_verify_fw(D):
				logging.debug("Firmware downloaded and verified!")
				status.append(D.get_device_status())
# 				D.send_message("Firmware correct")
				if M.install_fw(D, status):
					logging.debug("Update finished!")
					status.append(D.get_device_status())
					D.send_message("Update done")
					# send status before restart
					D.send_device_status(status)
					D.restart()
			else:
				D.send_exception("Update failed")
				logging.debug("Download or installation failed")
				# if update fails, also send status
				D.send_device_status(status)
		else:
			D.send_exception("Manifest incorrect")
			logging.debug("Manifest format is incorrect")
	elif ret == 0:
		D.send_exception("Could not get manifest")
		logging.debug("Could not get manifest from Konker")
	else:
		logging.debug("No manifest available")

	# D.send_device_status(status)
	# for debugging
# 	if num < 3:
# 		t = Timer(10, periodic_run, [D,M])
# 		t.start()

def main(argv):
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
	logging.debug("Starting update check")
	configuration = read_last_conf()
	if configuration == '':
		logging.debug("Failed to read configuration")
		return
	user = configuration['user']
	passwd = configuration['pwd']
	M = Manifest(user,passwd)
	D = Device(user,passwd)
	# start collecting device informatio and check if it's the first time a FW is running
	status = list([D.get_device_status()])
	# run indefnetly
	while(1):
		periodic_run(D,M, status)
		status = []
		sleep(10) #10s

if __name__ == "__main__":
	main(sys.argv)
