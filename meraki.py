import hassapi as hass
import requests
import json

DEFAULT_HOST = "https://api.meraki.com/api/v1/"
TIMESPAN = 2592000
BLOCK = '102'
ALLOW = '103'

#
# Meraki API App
#
# Args:
#

class MerakiAPI(hass.Hass):
  
  def initialize(self):
    self.log("Hello from Meraki API")
    self.meraki_secret=self.args["meraki_secret"]
    self.meraki_validator=self.args["meraki_validator"]
    self.meraki_api=self.args["meraki_api"]
    self.netID=self.args["meraki_net"]
    self._headers = {
      "X-Cisco-Meraki-API-Key": self.meraki_api,
      "Content-Type": "application/json",
      "Accept": "*.*",
    }
    self._allow_payload = '{"groupPolicyId": "103", "devicePolicy": "Group policy"}'
    self._block_payload = '{"groupPolicyId": "102", "devicePolicy": "Group policy"}'
    self.host=DEFAULT_HOST
    self.devices={}
    self.run_every(self.update_devices, "now", 6*3600)
    self.run_every(self.update_known_devices, "now+300", 60)
    self.listen_event(self.call_service, event = "call_service")
    #self.listen_event(self.events)
    
  def events(self,event_name,data, kwargs):
    if "climate" in data["entity_id"]:
      self.log(event_name)
      self.log(data)
  
  def update_devices(self, kwargs):
    self.log("Begin entity discovery")
    url = (self.host + "networks/" + self.netID + "/clients?timespan=" + str(TIMESPAN) + "&perPage=1000")
    payload={}
    device={}
    response = requests.request("GET", url, headers=self._headers, data=payload)
    meraki_devices = json.loads(response.text.encode("utf8"))
    counter=0
    num_meraki=len(meraki_devices)
    num_entities=0
    for meraki_device in meraki_devices:
      device = self.parseMerakiDevice(meraki_device)
      counter+=1
      num_entities=len(self.devices)
      if counter % 5 == 0:
        self.log("Progress: MerakiAPI found %d devices, completed %d, and %d are of interest", num_meraki, counter, num_entities)
    self.log("Completd: MerakiAPI found %d devices, completed %d, and %d are of interest", num_meraki, counter, num_entities)
    
  
  def parseMerakiDevice(self, meraki_device):
    device = {}
    device["attributes"]={}
    device["description"]="None"
    try:
      if meraki_device["description"] is not None:
        device["description"] = meraki_device["description"]
    except (Exception) as e:
      device["description"] = "None"
    device["id"]=meraki_device["id"]
    device["status"]=meraki_device["status"]
    device["attributes"]["mac"]=meraki_device["mac"]
    device["attributes"]["ip"]=meraki_device["ip"]
    device["attributes"]["os"]=meraki_device["os"]
    device["attributes"]["manufacturer"]=meraki_device["manufacturer"]
    device["attributes"]["vlan"]=meraki_device["vlan"]
    #device["attributes"]["ssid"]=meraki_device["ssid"]
    #device["attributes"]["switchport"]=meraki_device["switchport"]
    device["attributes"]["friendly_name"]="Meraki " + device["description"] + " " + device["attributes"]["mac"]
    device["attributes"]["entity_id"]="switch.meraki_" + device["id"]
    device = self.get_policy(device)
    if device["gp_id"] == '103' or device["gp_id"] == '101':
      device["state"]="on"
    else:
      device["state"]="off"
    if device["p_type"] == "Group policy" and (device["gp_id"] == '101' or device["gp_id"] == '102' or device["gp_id"] == '103'):
      self.devices[device["attributes"]["entity_id"]]=device
      self.set_state(device["attributes"]["entity_id"], state = device["state"], attributes = device["attributes"])
    return device
  
  def update_known_devices(self, kwargs):
    for device in self.devices:
      self.update_device(self.devices[device]["id"])
  
  def get_policy(self, device):
    policy_url = (self.host + "networks/" + self.netID + "/clients/" + device["id"] + "/policy")
    payload={}
    response = requests.request("GET", policy_url, headers=self._headers, data=payload)
    policy = json.loads(response.text.encode("utf8"))
    device["p_type"] = "Normal"
    try:
      device["p_type"] = policy["devicePolicy"]
    except (Exception) as e:
      self.log(e)
      self.log(policy)
      device["p_type"] = "Normal"
    if device["p_type"] != "Group policy":
      device["gp_id"] = 0
    else:
      device["gp_id"] = policy["groupPolicyId"]
    return device
  
  def set_policy(self, device, policyId):
    url = (self.host + "networks/" + self.netID + "/clients/provision")
    payload = json.dumps({
    "clients": [{"clientId": device["id"], "mac": device["attributes"]["mac"], "name": device["description"]}],
    "groupPolicyId": policyId, "devicePolicy": "Group Policy"
    }, indent=4)
    response = requests.request("POST", url, headers=self._headers, data=payload)
    self.log(response.text.encode("utf8"))
    self.update_device(device["id"])
    
  def update_device(self, deviceId):
    url = (self.host + "networks/" + self.netID + "/clients/" + deviceId)
    response = requests.request("GET", url, headers=self._headers, data={})
    meraki_device=json.loads(response.text.encode("utf8"))
    self.parseMerakiDevice(meraki_device)
  
  def call_service(self,event_name,data, kwargs):
    if not (data["domain"]=="switch" and "meraki_" in data["service_data"]["entity_id"]):
      return
    elif data["service"]=="turn_on":
      self.turn_on(data)
    elif data["service"]=="turn_off":
      self.turn_off(data)
    elif data["service"]=="toggle":
      self.turn_off(data)
    
  def toggle(self, data):
    self.log("toggle")
    id = data["service_data"]["entity_id"]
    if self.devics[id]["state"]=="on":
      self.turn_off(data)
    else:
      self.turn_on(data)
  
  def turn_on(self, data):
    self.log("turn_on")
    id = data["service_data"]["entity_id"]
    self.set_policy(self.devices[id], ALLOW)
    
  def turn_off(self, data):
    self.log("turn_off")
    id = data["service_data"]["entity_id"]
    self.set_policy(self.devices[id], BLOCK)
    
  
