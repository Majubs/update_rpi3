#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 19:31:29 2020

@author: majubs
"""
import sys, json
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
		print("Configuration file not found. Cannot access platform.")
	
	return conf

def periodic_run(D, M, status):
# 	global num
# 	num = num+1
	
	# check if its the first start of a new FW
	if D.check_first_start():
		print("Starting a new FW")
		if D.check_start():
			print("New version: ", D.version)
			status.append(D.get_device_status())
			D.send_message("Update correct")
		else:
			print("New FW did not start correctly")
			D.send_exception("Update incorrect")
			D.rollback()
		return
	else:
		print("Starting OTA process")
	
	if M.get_manifest():
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
			if M.apply_manifest(D):
				print("Update finished!")
				status.append(D.get_device_status())
				D.send_message("Rebooting")
				D.send_device_status(status)
				D.restart()
		else:
			D.send_exception("Manifest incorrect")
			print("Manifest format is incorrect")
	else:
		D.send_exception("Could not get manifest")
		print("Could not get manifest from Konker")

	# D.send_device_status(status)
	# for debugging
# 	if num < 3:
# 		t = Timer(10, periodic_run, [D,M])
# 		t.start()

def main(argv):
	print("Starting update check")
	configuration = read_last_conf()
	if configuration == '':
		print("Failed to read configuration")
		return
	#user = 'hheb89ujfuol'
	#passwd = 'xDQzzp0aYDbX'
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