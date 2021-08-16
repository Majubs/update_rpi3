#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 14:28:43 2020

@author: majubs
"""
import requests, hashlib, logging
# from time import sleep

class Manifest:
	errors_msg = [
		"Older version",
		"Update for different device",
		"Older sequence number",
		"Firmware URL missing",
		"Key claims missing"
		"Invalid digital signature",
		"Checksum missing",
		"Vendor ID invalid",
		"Not enough memory to update",
		"Minimum required version not found",
		"Version not in required version list",
		"Dependencies not met",
		"Author does not have permission"]
	
	def __init__(self,user,passwd):
		self.m_json = {}
		self.m_parsed = {}
		self.required_elements = ["version", "device", "sequence_number", "key_claims", "digital_signature", "checksum"]
		self.optional_elements = ["fw_url","vendor_id", "size", "required_version", "required_version_list", "dependencies", "author", "firmware", "payload_format", "processing_steps", "additional_steps", "encryption_wrapper"]
		self.valid = True
		self.user = user
		self.passwd = passwd
		self.new_fw = ''
		
	def _print_errors(self, err_filter):
		# print("Errors parsing manifest:", err_filter)
		errs = [e for (e, i) in zip(self.errors_msg, err_filter) if i]
		for e in errs:
			logging.debug("[ERRROR] %s", e)
	
	def get_manifest(self):
		logging.debug("Retrieving manifest from Konker Platform")
		try:
			r = requests.get('http://data.prod.konkerlabs.net/sub/' + self.user + '/_update', auth=(self.user, self.passwd))
		except:
			return 0
		#get manifest from addr
		logging.debug("Status: %d %s", r.status_code, r.reason)
		
		if r.status_code == 200:
			# empty list means there is no manifest
			if r.json() == []:
				return 2
			json_temp = r.json()[0]['data']

			if ("update stage" in json_temp) or ("update exception" in json_temp):
				return 2

			self.m_json = json_temp
			#r = r.text.replace("\'", "\"")
			#self.m_json = json.loads(r)
# 			print(json.dumps(self.m_json, indent=4))
			
			return 1
		
		return 0
	
	def parse_manifest(self, device):
		logging.debug("Parsing and validating manifest")
		self.valid = True
		
		# check_errs will de used as a filter for error messages, a True element means error ocurred
		# device.check_* functions return True if check is OK
		# so check_errs elements receive the negated result of device.check_* funtions
		check_errs =  []
		for field in self.required_elements:
			logging.debug("Check for required element %s", field)
			if field in self.m_json and self.m_json.get(field) != None:
				if field == "version":
					check_errs.append(not device.check_version(self.m_json.get(field)))
				elif field == "device":
					check_errs.append(not device.check_device(self.m_json.get(field)))
				elif field == "sequence_number":
					check_errs.append(not device.check_sequence_number(self.m_json.get(field)))
				elif field == "digital_signature":
					check_errs.append(not device.check_signature(self.m_json.get(field), self.m_json.get("key_claims")))
				else: #will be used later
					check_errs.append(False)
					self.m_parsed[field] = self.m_json.get(field)
			else:
				logging.debug("Required element missing from manifest: %s", field)
				check_errs.append(True)
# 				self.valid = False
			
# 		print(">>> Required elements: ", self.valid)
		for field in self.optional_elements:
			logging.debug("Checking for optional element %s", field)
			if field in self.m_json and self.m_json.get(field) != None:
				if field == "vendor_id":
					check_errs.append(not device.check_vendor(self.m_json.get(field)))
				elif field == "size":
					check_errs.append(not device.check_memory(self.m_json.get(field)))
				elif field == "required_version":
					check_errs.append(not device.check_min_version(self.m_json.get(field)))
				elif field == "required_version_list":
					check_errs.append(not device.check_version_list(self.m_json.get(field)))
				elif field == "dependencies":
					check_errs.append(not device.check_dependencies(self.m_json.get(field)))
				elif field == "author":
					check_errs.append(not device.check_permissions(self.m_json.get(field)))
				else:
					check_errs.append(False)
					self.m_parsed[field] = self.m_json.get(field)
			else:
				check_errs.append(False)
				logging.debug("Optional element NOT in manifest: %s", field)
		
		# check if any error occured
		incorrect = False
		for e in check_errs:
			incorrect = incorrect or e #one True will chance incorrect to True
		if incorrect:
			self.valid = False
			self._print_errors(check_errs)
	
#	def apply_manifest(self, device, status):
	def download_verify_fw(self, device):
		logging.debug("Applying manifest!")
		#update FW
		# print(self.m_parsed)
		self.new_fw = device.download_firmware()
		if self.new_fw == '':
			device.send_exception("Firmware not found")
			logging.debug("Did not receive firmware")
			return False
		else:
			device.send_message("Firmware received correctly")
# 		else:
# 			try:
# 				open('temp_fw.zip', 'wb').write(new_fw)
# 			except:
# 				print("Failed to save new FW to memory")
# 				return False
		
		md5sum = hashlib.md5(bytes(self.new_fw)).hexdigest()
		logging.debug("Received file checksum >>> ", md5sum)
		if device.check_checksum(self.m_parsed['checksum'], md5sum):
			device.send_message("Checksum OK")
			logging.debug("Checksum correct!")
			return True
		else:
			device.send_exception("Checksum did not match")
			logging.debug("Checksum incorrect!")
			return False
		

	def install_fw(self, device, status):
		#do processing stuff (if needed)
		alg = 'zip'
		if 'processing_steps' in self.m_parsed:
			logging.debug("Doing processing steps: ", self.m_parsed['processing_steps'][0])
			p_steps = self.m_parsed['processing_steps'][0]
			if p_steps.get('decode_algorithm'):
				alg = p_steps['decode_algorithm']

			if p_steps.get('run'):
				if not device.run_cmd_install(p_steps['run']):
					return False

		#write new FW to device
		new_fw_fname = device.write_file(self.new_fw, self.m_json.get('version'), alg)
		
		#substitute olf FW with new
		logging.debug("Applying new firmware")
		status.append(device.get_device_status())
		device.apply_firmware(new_fw_fname, (self.m_json.get("version"), self.m_json.get("sequence_number"), self.m_json.get("size"), self.m_json.get("expiration_date"), self.m_json.get("author"), self.m_json.get("digital_signature"), self.m_json.get("key_claims"), self.m_json.get("checksum")))

		# after update (if needed)
		if 'additional_steps' in self.m_parsed:
			logging.debug("Doing addtional steps: ", self.m_parsed['additional_steps'][0])

		return True
