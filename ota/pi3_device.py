#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 18:50:59 2020

@author: majubs
"""
import json, requests, os, platform, subprocess, psutil, socket, logging
from zipfile import ZipFile
from time import time

class Device:
	# load device information for checks later
	def __init__(self, user, passwd, fw_info_file="fw_info.json"):
		try:
			with open(fw_info_file, 'r') as f:
				content = json.loads(f.read())
			print("Device information: ")
			print(json.dumps(content, indent=4))
                
			if content.get("version"):
				self.version = content["version"]
			else:
				self.version = '0.0.0'
			if content.get("device"):
				self.device = content["device"]
			else:
				self.device = socket.gethostname()
			if content.get("sequence_number"):
				self.sequence_number = content["sequence_number"]
			else:
				self.sequence_number = '9999999999999'
			if content.get("backup"):
				self.backup_file = content["backup"]
			else:
				self.backup_file = "fw.zip"
		except:
			self.version = '0.0.0'
			self.device = 'node00'
			self.sequence_number = '9999999999999'
			self.backup_file = "fw.zip"
# 		self.directory_list = ['conf', 'rtd-LoRa', 'master'] #, 'ota']
		self.directory_list = ['app']
		self.fw_info_file = fw_info_file
		self.start_file = "../app/start"
		self.user = user
		self.passwd = passwd
		self.last_milli_time = round(time() * 1000)
		
	#backup current FW in zip format
	def _backup_fw(self, dirs=''):
		if dirs:
			self.directory_list = dirs
		
		out_file = "fw_" + self.version + ".zip"
		try:
			zip_obj = ZipFile(out_file, 'w')
		
			logging.debug("[DEV] Backing up current FW, version ", self.version)
			
			os.chdir('../')
			for d in self.directory_list:
				for folderName, subfolders, filenames in os.walk(d):
					for filename in filenames:
						print("[DEV] Adding file: ", folderName + '/' + filename)
						filePath = os.path.join(folderName, filename)
						zip_obj.write(filePath)
			os.chdir('ota/')
			zip_obj.write(self.fw_info_file)
			zip_obj.close()
		except:
			logging.debug("[DEV] It was not possible to create a backup")
		
# 		os.rename(out_file, 'ota/' + out_file)
		self.backup_file = out_file
		
	#update FW information file with new FW information
	def _update_fw_info(self, new_info):
		with open(self.fw_info_file, 'r') as f:
			content = json.loads(f.read())
			
		content["version"] = new_info[0]
		content["sequence_number"] = new_info[1]
		content["size"] = new_info[2]
		content["expiration_date"] = new_info[3]
		content["author"] = new_info[4]
		content["digital_signature"] = new_info[5]
		content["key_claims"] = new_info[6]
		content["checksum"] = new_info[7]
		content["backup"] = self.backup_file

		with open(self.fw_info_file, 'w') as f:
			f.write(json.dumps(content))

		self.version = new_info[0]
		self.sequence_number = new_info[1]
			
	# Return True if ver1 > ver2, False otherwise
	def _compare_versions(self, ver1, ver2):
		# print('Version NEW: '+ str(ver1))
		# print('Version OLD: '+ str(ver2))
		v1 = ver1.split('.')
		v2 = ver2.split('.')
		if v1[0] > v2[0]:
			return True
		if v1[0] == v2[0]:
			if v1[1] > v2[1]:
				return True
			if v1[1] == v2[1]:
				if v1[2] > v2[2]:
					return True
		return False
	
	def check_dependencies(self, deps_list):
		return True
	
	def check_device(self, device_type):
		return self.device == device_type
	
	def check_memory(self, fw_size):
		return True
	
	def check_min_version(self, req_version):
		if self.version == req_version:
			return True
		return self._compare_versions(self.version, req_version)
	
	def check_permissions(self, author):
		return True
	
	def check_sequence_number(self, seq_number):
		return int(self.sequence_number) < int(seq_number)
	
	def check_signature(self, signature, key_claims):
		return True
	
	def check_vendor(self, vendor_id):
		return True
	
	def check_version(self, new_version):
		return self._compare_versions(new_version, self.version)
	
	def check_version_list(self, req_version_list):
		if self.version in req_version_list:
			return True
		return False
	
	def download_firmware(self):
		logging.debug("[DEV] Retrieving FIRMWARE from Konker")
		#get manifest from addr
		try:
			r = requests.get('https://data.prod.konkerlabs.net/firmware/' + self.user + '/binary', auth=(self.user, self.passwd))
		except:
			return ''
		logging.debug("[DEV] Status: ", r.status_code, r.reason)
		
		if r.status_code == 200:
			# if it's a FW, the Content-type is application/octet-stream
			if r.headers['Content-type'].split(';')[0] == 'application/json':
				return ''
			new_fw = r.content
			# print("=======================================================")
			# print(bytes(new_fw))
			# print("=======================================================")
			
			return new_fw
		
		return ''
	
	def check_checksum(self, md5_recv, md5_calc):
		return md5_calc == md5_recv
	
	#backup old FW and extract new one
	def apply_firmware(self, new_fw, fw_info, steps=None):
		if steps:
			logging.debug("-> ", steps)
			
		self._backup_fw()
		
		#decompress new FW
		with ZipFile(new_fw, 'r') as zip_obj:
			zip_list = zip_obj.namelist()
			if 'fw_info.json' in zip_list:
				zip_obj.extract('fw_info.json')
				zip_list.remove('fw_info.json')
			zip_obj.extractall('../app/', zip_list)
		
		self._update_fw_info(fw_info)

	def run_cmd_install(self, cmd):
		if cmd:
			return_code = subprocess.run(cmd.split(), cwd="../app/")

			if return_code == 0:
				return True

		return False

	# write the new fw to flash
	def write_file(self, fw, version, alg):
		file_name = "fw_" + version + "." + alg
		with open(file_name, 'wb') as f:
			f.write(fw)
			
		return file_name
	
	# return True if its the first start of a new FW, False otherwise
	def check_first_start(self):
		if os.path.isfile(self.start_file):
			os.remove(self.start_file)
			return True
		return False
	
	def rollback(self):
		if os.path.isfile(self.backup_file):
			#decompress old FW
			os.chdir('../')
			with ZipFile(self.backup_file, 'r') as zip_obj:
				zip_list = zip_obj.namelist()
				if 'fw_info.json' in zip_list:
					zip_obj.extract('fw_info.json', 'ota/')
					zip_list.remove('fw_info.json')
				# extract fw_info file
				zip_obj.extractall(os.getcwd(), zip_list)
				
			os.chdir('ota')
			logging.debug("[DEV] Rollback done")
		else:
			logging.debug("[DEV] Backup does not exists!")
		
	# restart FW
	def restart(self):
		logging.debug("[DEV] Reestarting FW")
		#subprocess.call('sudo supervisorctl restart gateway_update', shell=True)
		# create file to indicate the first start of a new FW
		with open(self.start_file, 'w') as f:
			f.write("1")
			
	# returns ping to platform in ms
	def ping_platform(self):
		host = 'konkerlabs.com'
		
		# Option for the number of packets as a function of
		param = '-n' if platform.system().lower()=='windows' else '-c'
	
		# Building the command. Ex: "ping -c 1 google.com"
		command = ['ping', param, '5', host]
	
		r = subprocess.run(command, stdout=subprocess.PIPE)
# 		print("Result:", r)
		
		separator = '\\r\\n' if platform.system().lower()=='windows' else '\\n'
		if r.returncode == 0:
			r_str = str(r.stdout).split(separator)
			# print(r_str)
			ret_ping = float(r_str[-2].split('/')[4])
	# 		r_str = r_str.split('\\')
	# 		print('>>> ', r_str[-2])
		else:
			ret_ping = 0.0
		
		return ret_ping
	
	def get_signal_strength(self):
		command = "iwconfig wlan0".split()
		quality = 0
		strength = 0

		r = subprocess.run(command, stdout=subprocess.PIPE)

		if r.returncode == 0:
			o = str(r.stdout)
			idx_start = o.find("Link")
			if idx_start >= 0:
				idx_end = o[idx_start:].find("\\n")
				l = o[idx_start:idx_end]
				q = l.split()[1]
				s = l.split()[4]
				quality = q.split('=')[1].split('/')[0]
				strength = s.split('=')[1]

		return quality, strength

	# return a dict with ping and nmap info
	def get_network_info(self):
		ping = self.ping_platform()
		logging.debug("[DEV] Ping is {} ms".format(ping))
		
		quality, strength = self.get_signal_strength()
		logging.debug("[DEV] Signal information {}/70 | {} dBm".format(quality, strength))

		# TODO get this info
		nmap = {}
		
		info = {"ping":ping, "signal_quality":quality, "signal_strength":strength} #"nmap":nmap}
		
		return info
	
	# returns a list of dicts, of top 5 processes by cpu utilization
	# each dict has PID, COMM, CPUTIME, MEM, CPU from ps
	def top_processes(self):
		command = "ps -eo pid,comm,cputime,%mem,%cpu --sort -%cpu,-%mem --no-headers".split()
		
		procs = subprocess.run(command, stdout=subprocess.PIPE)
# 		print("Result:", procs)
		top_procs = []
		
		if procs.returncode == 0:
			procs = str(procs.stdout).split('\\n')[1:]
			num_procs = len(procs)
			if num_procs > 5:
				num_procs = 5
			
			for p in procs[:num_procs]:
				l = p.split()
				if l and len(l) == 5:
					top_procs.append({"pid":l[0], "comm":l[1], "time":l[2], "mem":l[3], "cpu":l[4]})
		# print("Top processes: \n", top_procs)
			
		return top_procs
	
	#measure device temperature
	def measure_temp(self):
		temp = os.popen("vcgencmd measure_temp").readline()
		if temp == '':
			ret_temp = 0.0
		else:
			temp = temp.replace("'C","").replace("temp=", "")
			ret_temp = float(temp)
		
		return ret_temp
	
	# returns a dict with cpu utilization, memory utilization, 
	#	timestamp delta (since last call of this function), device temperature,
	#	top 5 processes
	def get_device_status(self):
		cpu = psutil.cpu_percent()
		mem = psutil.virtual_memory().available 
		
		current_milli_time = round(time() * 1000)
		temp = self.measure_temp()
		top_procs = self.top_processes()
		
		status = {"cpu": cpu, "mem":mem, "temp":temp, "ts_diff":current_milli_time-self.last_milli_time, "ps":top_procs}
		self.last_milli_time = current_milli_time
		
		# print(status)
		
		return status
		
	# return True if all processes started correctly and communication is working, False otherwise
	def check_start(self):
		return True
	
	# send things to platform
	def send_message(self, msg):
		data = json.dumps({"update stage":msg})
		try:
			requests.post('http://data.prod.konkerlabs.net/pub/' + self.user + '/_update_in', auth=(self.user, self.passwd), data=data)
		except:
			logging.debug("[DEV] Message not sent")
		logging.debug("[DEV] Sending: %s", msg)
		
	def send_exception(self, exception):
		data = json.dumps({"update exception":exception})
		try:
			requests.post('http://data.prod.konkerlabs.net/pub/' + self.user + '/_update_in', auth=(self.user, self.passwd), data=data)
		except:
			logging.debug("[DEV] Message not sent")
		logging.debug("[DEV] Exception: %s", exception)
		
	def send_device_status(self, status_list):
		logging.debug("[DEV] Sending status colllected during execution")
		
		for s in status_list:
			data = json.dumps(s)
			try:
				requests.post('http://data.prod.konkerlabs.net/pub/' + self.user + '/_update_in', auth=(self.user, self.passwd), data=data)
			except:
				logging.debug("[DEV] Status not sent")
			# print("[DEV] Sending: ", s)
			
		logging.debug("[DEV] Done sending")
