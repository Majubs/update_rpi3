#!/usr/bin/python3

import requests, json, hashlib, os, sys, time
import connect_platform as platform
import paho.mqtt.publish as publish

class Firmware:
	def __init__(self, file, md5_file, version):
		self.file = file
		self.md5_file = md5_file
		self.version = version
		
	def print_fw(self):
		print("==========================================")
		print("File:\t\t", self.file)
		print("Chacksum:\t", self.md5_file)
		print("Version:\t", self.version)
		print("==========================================")
		
	def get_files_content(self):
		f = open(self.file, 'rb')
		if(os.path.isfile(self.md5_file)):
			md5sum = open(self.md5_file, 'rb')
		else:
			md5sum = hashlib.md5(f.read()).hexdigest()
		return f, md5sum
	
	def _get_checksum(self):
		if(os.path.isfile(self.md5_file)):
			md5file = open(self.md5_file, 'r')
			md5sum = md5file.read().split()[0]
			md5file.close()
		else:
			f = open(self.file, 'rb')
			md5sum = hashlib.md5(f.read()).hexdigest()
			content = "{} {}".format(md5sum, self.file.split('/')[-1])
			with open(self.md5_file, 'w') as md5file:
				md5file.write(content)
			f.close()
			
		print("MD5SUM = ", md5sum)
		return md5sum

################################# End of class Firmware ############################################

class DeviceInfo:
	def __init__(self, name, guid, dev_id):
		self.name = name
		self.guid = guid
		self.dev_id = dev_id
		
	def set_status(self, status):
		self.status = status
		
	def set_version(self, version):
		self.version = version
		
	def set_upload_info(self, data):
		self.upload_info = data

################################# End of class DeviceInfo ############################################

class Device(Firmware, DeviceInfo):
	def __init__(self, name, guid, dev_id, file, md5sum, version):
		Firmware.__init__(self, file, md5sum, version)
		DeviceInfo.__init__(self, name, guid, dev_id)
		
	def get_fw_info(self):
		return Firmware(self.file, self.md5_file, self.version)

################################# End of class Device ############################################

def create_fw_req(plat, header, fw):
	file, md5sum = fw.get_files_content()
	multipart_form_data = {'firmware': file, 'checksum': md5sum}
	fw.print_fw();
	
	print("Sending...")
	r = requests.request('POST', url="{}/{}/firmwares/{}".format(plat.api, plat.params['application'], plat.params['deviceModelName']), headers=header, params={'version': fw.version}, files=multipart_form_data)
	
	return r

def create_update_req(plat, header, device):
	data = {"deviceGuid": device.guid, "status": "PENDING", "version": device.version}
#	json_body = json.dumps(data)
	
	print(">> Headers: ", header)
	print(">> Body: ", json.dumps(data))
	
	print("Sending...")
	r = requests.request('POST', url="{}/{}/firmwareupdates/".format(plat.api, plat.params['application']), headers=header, json=data)
	print("PreparedRequest => ", r.request.path_url, r.request.body)
	
	return r

def request(req_type, plat, header, device):
	# Send request
	print("Creating {} request".format(req_type))

	if req_type == 'fw':
		r = create_fw_req(plat, header, device.get_fw_info())
	else:
		r = create_update_req(plat, header, device)

#	print("Return header ", r.headers)
	print("Endpoint ", r.url)
	print("Status: ", r.status_code, r.reason)

	# Extract data from response in json format
	data = r.json()

	print("Data returned:")
	print(json.dumps(data, indent=4))
	
	return r.status_code, data
	
# Entire process to create an update
def new_fw(plat, device):
	print("Creating update for device", device.name)
	r, data = request('fw', plat, plat.header, device)
	if (r != 200) and (data['status'] != 'success'):
		print("Failed to create update for device ", device.name)
		return False
	device.set_upload_info(data['result'])
	header = {"Content-Type": "application/json"}
	header.update(plat.header)
#	header['Authorization'] = header['Authorization'].format(token['access_token'])
	r, data = request('update', plat, header, device)
	if (r != 200) and (data['status'] != 'success'):
		print("Failed to create update for device ", device.name)
		return False
		
	return True

def create_updates(plat, devices):
	ok = True
	for d in devices:
		ok = ok and new_fw(plat, d)
	
	return ok

def create_manifests(plat, devices_list):
		man = {"sequence_number": str(int(time.time() * 1000)), "key_claims": "something", "digital_signature": "1234567890alongstringhgeresignature0"} #, "required_version_list": ["1.0.10", "1.0.0", "0.0.0"]}
		
		for d in devices_list:
			man_d = man
			man_d["version"] = d.version
			man_d["size"] = os.path.getsize(d.file)
			man_d["device"] = d.dev_id
			man_d["checksum"] = d._get_checksum()
			
			channel = "data/{}/pub/_in".format("svh462pj3v19")
			device_auth = {"username": "svh462pj3v19", "password": "saxgjM4CmqVz"}
			
			print("Sending device manifest to: ", channel)
			print(man_d)
			
			publish.single(channel, payload=json.dumps(man_d), hostname="mqtt.prod.konkerlabs.net", port=1883, auth=device_auth)

def main(argv):
	p = platform.Platform(user = "mjuliabs@gmail.com", pwd = "xaengu5Ukonker", api="https://api.prod.konkerlabs.net:443/v1")
					   #api="http://192.168.0.123:8081/v1")
	devices = []
	dev_id = 'rpi3'
	dev_guid = 'f51b38a8-351d-448a-aa6d-549e1b66258a'
	dev_name = 'Raspberry'
	fwbin_file = '/home/majubs/Documents/Mestrado/update_rpi3/new_fw/new_app.zip'
	md5_file = '/home/majubs/Documents/Mestrado/update_rpi3/new_fw/new_app.txt'
	v = '1.0.9'
	devices.append(Device(dev_name, dev_guid, dev_id, fwbin_file, md5_file, v))
	
# 	ok = create_updates(p, devices)
# 	if ok:
# 		print("Updates created.")
# 	else:
# 		print("It was not possible to create update for all devices!")
#		return

	create_manifests(p, devices)

if __name__ == "__main__":
	main(sys.argv)