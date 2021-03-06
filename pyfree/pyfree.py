#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pyfree!

import os
import datetime
import time
import requests
import json
import hmac
from hashlib import sha1
import base64


APP_TOKEN_FILE = '.app_token'

LOCAL_FREEBOX_URL = 'http://mafreebox.freebox.fr/'

API_VERSION    = 'api_version'
API_BASE_URL   = 'api/'

LOGIN          = 'login/'
LOGIN_AUTH     = 'login/authorize/'
LOGIN_SESSION  = 'login/session/'

CONTACT        = 'contact/'

CALL_LOG       = 'call/log/'

LCD            = 'lcd/config/'

WIFI           = 'wifi/config/'

REBOOT         = 'system/reboot/'

LIST_FILE      = 'fs/ls/'
DOWNLOAD_FILE  = 'dl/'


class Freebox():

	def __init__(self, freebox_ip=None, freebox_port=None, debug=False):
		if os.path.isfile(APP_TOKEN_FILE):
			self._app_tocken = open(APP_TOKEN_FILE, 'r').read()

		if freebox_port is not None and freebox_ip is not None:
			self._freebox_url = 'http://' + freebox_ip + ':' + freebox_port + '/'
		else:
			self._freebox_url = LOCAL_FREEBOX_URL

		version = str(self.api_version.find('.'))
		if freebox_port is not None and freebox_ip is not None:
			self._base_url = 'http://' + freebox_ip + ':' + freebox_port + '/' + API_BASE_URL + 'v' + version + '/'
		else:
			self._base_url = LOCAL_FREEBOX_URL + API_BASE_URL + 'v' + version + '/'

		self._debug = debug

	def is_authorization_granted(self):
		"""
			Return True if an authorization has already been granted on the freebox.
		"""
		return True if os.path.isfile(APP_TOKEN_FILE) else False

	def ask_authorization(self, app_id, app_name, app_version, device_name):
		"""
			This must be call the first time the application is lauched.
			An authorization has to be done directly on the Freebox.
			See http://dev.freebox.fr/sdk/os/login/
		"""
		parameter = {"app_id": app_id, "app_name": app_name, "app_version": app_version, "device_name": device_name}
		authorization_reponse = self._request_to_freebox(self._base_url + LOGIN_AUTH, 'POST', parameter)

		if (authorization_reponse["success"] is not True):
			return None

		track_id = str(authorization_reponse["result"]["track_id"])

		while True:
			authorization = self._request_to_freebox(self._base_url + LOGIN_AUTH + track_id, 'GET')
			if not authorization["result"]["status"] == 'pending':
				break
			time.sleep(1)

		if authorization["result"]["status"] == "granted":
			self._app_tocken = str(authorization_reponse["result"]["app_token"])
			open(APP_TOKEN_FILE, 'w').write(self._app_tocken)
			return self._app_tocken
		else:
			return None

	def login(self, app_id):
		"""
			This function has to be called after the authorization has been granted by the function ask_authorization.
		"""
		login_response = self._request_to_freebox(self._base_url + LOGIN, 'GET')

		if login_response["success"] is False:
			return None

		challenge = login_response["result"]["challenge"]

		password_bin = hmac.new(self._app_tocken, challenge, sha1)
		password  = password_bin.hexdigest()

		parameter = {"app_id": app_id, "password": password}
		login_response = self._request_to_freebox(self._base_url + LOGIN_SESSION, 'POST', parameter)

		if login_response["success"] is True:
			self._session_tocken = str(login_response["result"]["session_token"])

		return self._session_tocken

	##########################################################################

	def get_call_list(self):
		"""
			Access the Freebox call logs.
			See http://dev.freebox.fr/sdk/os/call/
		"""
		call_list = self._request_to_freebox(self._base_url + CALL_LOG, 'GET')
		return call_list

	def _is_calling_today(self, timestamp):
		if str(datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')) == str(datetime.date.today()):
			return True
		else:
			return False

	def get_missed_call(self, today=False, convert_date=True):
		"""
			Return missing call generator.
			See http://dev.freebox.fr/sdk/os/call/
		"""
		missed_call = []
		call_list = self.get_call_list()

		if call_list["success"] is False:
			return missed_call

		for call in call_list["result"]:
			if ((self._is_calling_today(call["datetime"]) is True) and call["type"] == "missed"):
				if convert_date is True:
					call["datetime"] = str(datetime.datetime.fromtimestamp(call["datetime"]).strftime('%H:%M:%S - %d/%m/%Y'))
				missed_call.append(call)

		return missed_call

	##########################################################################

	def get_contact_list(self):
		"""
			Get list of contacts.
			See http://dev.freebox.fr/sdk/os/contacts/
		"""
		parameter = {"start": 1, "limit": 4, "group_id": 1}
		contact_list = self._request_to_freebox(self._base_url + CONTACT, 'POST', parameters=parameter)
		return contact_list

	def get_contact(self, contact_id):
		"""
			Access a given contact entry.
			See http://dev.freebox.fr/sdk/os/contacts/
		"""
		contact = self._request_to_freebox(self._base_url + CONTACT + contact_id, 'GET')
		return contact

	def create_contact(self, display_name=None, first_name=None, last_name=None):
		"""
			Create a contact.
			See http://dev.freebox.fr/sdk/os/contacts/
		"""
		parameter = {'display_name': display_name, 'first_name': first_name, 'last_name': last_name}
		create_contact_response = self._request_to_freebox(self._base_url + CONTACT, 'POST', parameters=parameter)
		return create_contact_response

	def delete_contact(self, contact_id):
		"""
			Delete a contact.
			See http://dev.freebox.fr/sdk/os/contacts/
		"""
		delete_contact = self._request_to_freebox(self._base_url + CONTACT + contact_id, 'GET')
		return delete_contact

	##########################################################################

	def get_lcd_config(self):
		"""
			Get the current LCD configuration.
			See http://dev.freebox.fr/sdk/os/lcd/
		"""
		lcd_config = self._request_to_freebox(self._base_url + LCD, 'GET')
		return lcd_config

	def update_lcd_config(self, brightness=None, orientation=None, orientation_forced=None):
		"""
			Update the current LCD configuration.
			See http://dev.freebox.fr/sdk/os/lcd/
		"""
		parameter = {'brightness': brightness, 'orientation': orientation, 'orientation_forced': orientation_forced}
		update_lcd_config_response = self._request_to_freebox(self._base_url + LCD, 'POST', parameters=parameter)
		return update_lcd_config_response

	###########################################################################

	def set_wifi_status(self, enabled=True):
		"""
			Change Wifi status (on/off)
			See http://dev.freebox.fr/sdk/os/wifi/
		"""
		parameter = {"bss": {"perso":{"enabled": enabled}}}
		parameter = {"ap_params": {"enabled": enabled}}
		set_wifi_status_response = self._request_to_freebox(self._base_url + WIFI, 'PUT', parameters=parameter)
		return set_wifi_status_response
	
	###########################################################################
	
	def reboot(self):
		"""
			Reboot Freebox
		"""
		# Cette application n'est pas autorisée à accéder à cette fonction : insufficient_rights
		self._request_to_freebox(self._base_url + REBOOT, 'POST')

	###########################################################################

	def get_file_list(self, directory):
		"""
			Get a list of files from a specific directory.
			See http://dev.freebox.fr/sdk/os/fs/#list-files
		"""
		# parameter = {'onlyFolder': False, 'countSubFolder': False, 'removeHidden': True}
		file_list = self._request_to_freebox(self._base_url + LIST_FILE + base64.b64encode(directory), 'GET')
		return file_list

	def download_file(self, file_path_b64, file_path_save):
		"""
			Dowload file 'file_path_b64' and save it at 'file_path_save'
			See http://dev.freebox.fr/sdk/os/fs/#download-a-file
		"""
		result = self._request_to_freebox(self._base_url + DOWNLOAD_FILE + file_path_b64, 'GET', is_response_json=False)
		open(file_path_save, 'w').write(result.content)

	###########################################################################

	@property
	def device_name(self):
		"""
			The device name "Freebox Server".
		"""
		version = requests.get(self._freebox_url + API_VERSION)
		return version.json()['device_name']

	@property
	def uid(self):
		"""
			The device unique id.
		"""
		version = requests.get(self._freebox_url + API_VERSION)
		return version.json()['uid']

	@property
	def api_version(self):
		"""
			The current API version on the Freebox.
		"""
		version = requests.get(self._freebox_url + API_VERSION)
		return version.json()['api_version']

	@property
	def device_type(self):
		"""
			“FreeboxServer1,1” for the Freebox Server revision 1,1
		"""
		version = requests.get(self._freebox_url + API_VERSION)
		return version.json()['device_type']

	@property
	def api_base_url(self):
		"""
			The API root path on the HTTP server.
		"""
		version = requests.get(self._freebox_url + API_VERSION)
		return version.json()['api_base_url']

	###########################################################################

	def _request_to_freebox(self, url, requestType, parameters=None, is_response_json=True):
		self.print_debug('--> ' + url)
		header = {'X-Fbx-App-Auth': self._session_tocken} if hasattr(self, '_session_tocken') else None
		if (requestType == 'GET'):
			response = requests.get(url, headers=header)
		if (requestType == 'POST'):
			response = requests.post(url, data=json.dumps(parameters), headers=header)
		if (requestType == 'PUT'):
			response = requests.put(url, data=json.dumps(parameters), headers=header)

		if is_response_json is True:
			response = response.json()
			if response["success"] is False:
				print 'Error ' + response["msg"].encode('utf-8') + ' : ' + response["error_code"].encode('utf-8')

		return response

	###########################################################################

	def print_debug(self, message):
		if self._debug:
			print message