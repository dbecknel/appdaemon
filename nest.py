import hassapi as hass
import requests
import json


#
# NEST API App
#
# Args:
#

class NESTAPI(hass.Hass):
  
  def initialize(self):
    self.log("Hello from NEST API")
    self.nest_refresh=self.args["nest_refresh"]
    self.nest_client_id=self.args["nest_client_id"]
    self.nest_client_secret=self.args["nest_client_secret"]
    self.nest_project_id=self.args["nest_project_id"]
    self.access_token=""
    self.devices={}
    self.get_token(self.args)
    self.run_every(self.update_devices, "now", 30)
    self.run_every(self.get_token, "now+3500", 3500)
    self.listen_event(self.call_service, event = "call_service")
    
  
  def get_token(self, kwargs):
    req_headers={}
    req_payload={}
    url="https://www.googleapis.com/oauth2/v4/token?client_id=" + self.nest_client_id + "&client_secret=" + self.nest_client_secret + "&refresh_token=" + self.nest_refresh + "&grant_type=refresh_token"
    response = requests.request("POST", url, headers=req_headers, data=req_payload)
    self.access_token=json.loads(response.text.encode('utf8'))["access_token"]
    
  def update_devices(self, kwargs):
    device = {}
    device["attributes"]={}
    url = "https://smartdevicemanagement.googleapis.com/v1/enterprises/"+self.nest_project_id+"/devices"
    payload = {}
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + self.access_token
    }
    response = requests.request("GET", url, headers=headers, data = payload)
    devices = json.loads(response.text.encode('utf8'))["devices"]
    for nest_device in devices:
      if "THERMOSTAT" in nest_device["type"]:
        device = self.parseThermostat(nest_device)
        self.devices[device["attributes"]["entity_id"]]=device
        self.set_state(device["attributes"]["entity_id"], state = device["state"], attributes = device["attributes"])
        self.set_state("sensor."+device["attributes"]["entity_id"].split(".")[1]+"_temp", state = device["attributes"]["current_temperature"], attributes = {"device_class" : "temperature", "friendly_name" : device["attributes"]["friendly_name"] + " Temperature"})
        self.set_state("switch."+device["attributes"]["entity_id"].split(".")[1]+"_switch", state = device["state"], attributes = {"friendly_name" : device["attributes"]["friendly_name"] + " Switch"})
  
  def parseThermostat(self, nest_device):
    device = {}
    device["attributes"]={}
    device["attributes"]["friendly_name"]=nest_device["parentRelations"][0]["displayName"] + " Nest Thermostat"
    device["nest_id"] = nest_device["name"]
    device["attributes"]["entity_id"]="climate." + device["attributes"]["friendly_name"].lower().replace(" ", "_")
    device["attributes"]["hvac_mode"]=nest_device["traits"]["sdm.devices.traits.ThermostatMode"]["mode"].lower().replace("heatcool", "heat_cool")
    device["attributes"]["preset_mode"]=device["attributes"]["hvac_mode"]
    device["attributes"]["hvac_modes"]=nest_device["traits"]["sdm.devices.traits.ThermostatMode"]["availableModes"]
    device["attributes"]["hvac_modes"]=[mode.lower().replace("heatcool", "heat_cool") for mode in device["attributes"]["hvac_modes"]]
    device["attributes"]["preset_modes"]=device["attributes"]["hvac_modes"]
    device["attributes"]["current_temperature"]=round(nest_device["traits"]["sdm.devices.traits.Temperature"]["ambientTemperatureCelsius"]*9/5+32, 1)
    device["attributes"]["current_humidty"]=nest_device["traits"]["sdm.devices.traits.Humidity"]["ambientHumidityPercent"]
    device["attributes"]["hvac_action"]=nest_device["traits"]["sdm.devices.traits.ThermostatHvac"]["status"].lower()
    device["attributes"]["supported_features"]=17
    if device["attributes"]["hvac_action"] == "off":
      device["attributes"]["hvac_action"]="idle"
    if "heat_cool" in device["attributes"]["hvac_modes"]:
      device["attributes"]["supported_features"]+=2
    if device["attributes"]["hvac_mode"] == "heat":
      device["state"]="on"
      device["attributes"]["temperature"]=round(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["heatCelsius"]*9/5+32, 1)
    elif device["attributes"]["hvac_mode"] == "cool":
      device["state"]="on"
      device["attributes"]["temperature"]=round(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["coolCelsius"]*9/5+32, 1)
    elif device["attributes"]["hvac_mode"] == "heat_cool":
      device["state"]="on"
      device["attributes"]["target_temp_low"]=round(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["heatCelsius"]*9/5+32, 1)
      device["attributes"]["target_temp_high"]=round(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["coolCelsius"]*9/5+32, 1)
    else:
      device["state"]="off"
    return device
  
  def call_service(self,event_name,data, kwargs):
    if data["domain"]!="climate":
      return
    if data["service"]=="set_hvac_mode":
      self.set_hvac_mode(data)
    elif data["service"]=="set_temperature":
      self.set_temperature(data)
    elif data["service"]=="turn_on":
      self.turn_on(data)
    elif data["service"]=="turn_off":
      self.turn_off(data)
    self.log(data)
  
  def set_hvac_mode(self, data):
    self.log("set_hvac_mode")
    id = data["service_data"]["entity_id"]
    payload = json.dumps({
      'command' : 'sdm.devices.commands.ThermostatMode.SetMode',
      'params' : {
        'mode' : data["service_data"]["hvac_mode"].replace("heat_cool", "heatcool").upper()
        }
      }, indent=4)
    self.post_api(self.devices[id], payload)
    
  def turn_on(self, data):
    self.log("turn_on")
    
  def turn_off(self, data):
    self.log("turn_off")
    payload = json.dumps({
      'command' : 'sdm.devices.commands.ThermostatMode.SetMode',
      'params' : {
        'mode' : 'OFF'
        }
      }, indent=4)
    self.post_api(self.devices[id], payload)
    
  def set_temperature(self, data):
    self.log("set_temperature")
    payload={}
    id=""
    if "entity_id" not in data["service_data"]:
      return
    else:
      id = data["service_data"]["entity_id"]
    if "hvac_mode" in data["service_data"]:
      if (data["service_data"]["hvac_mode"] == "heat" or data["service_data"]["hvac_mode"] == "cool") and "temperature" not in data["service_data"]:
        return
      elif data["service_data"]["hvac_mode"] == "heat_cool" and ("target_temp_high" not in data["service_data"] or "target_temp_low" not in data["service_data"]):
        return
      elif data["service_data"]["hvac_mode"] == "off":
        self.turn_off(data)
        return
      else:
        self.set_hvac_mode(data)
    if self.devices[id]["attributes"]["hvac_mode"] == "heat_cool":
      payload = json.dumps({
        "command" : "sdm.devices.commands.ThermostatTemperatureSetpoint.SetRange",
        "params" : {
          "coolCelsius" : round((data["service_data"]["target_temp_high"]-32)*5/9, 2),
          "heatCelsius" : round((data["service_data"]["target_temp_low"]-32)*5/9, 2)
          }
        }, indent=4)
      self.post_api(self.devices[id], payload)
    elif self.devices[id]["attributes"]["hvac_mode"] == "cool":
      payload = json.dumps({
        "command" : "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
        "params" : {
          "coolCelsius" : round((data["service_data"]["temperature"]-32)*5/9, 2)
          }
        }, indent=4)
      self.post_api(self.devices[id], payload)
    elif self.devices[id]["attributes"]["hvac_mode"] == "heat":
      payload = json.dumps({
        "command" : "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
        "params" : {
          "heatCelsius" : round((data["service_data"]["temperature"]-32)*5/9, 2)
          }
        }, indent=4)
      self.post_api(self.devices[id], payload)

  
  def post_api(self, device, payload):
    url = "https://smartdevicemanagement.googleapis.com/v1/"+device["nest_id"]+":executeCommand"
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + self.access_token
    }
    self.log(device["attributes"]["entity_id"])
    self.log(payload)
    response = requests.request("POST", url, headers = headers, data = payload)
    if json.loads(response.text.encode('utf8')) != {}:
      self.log(json.loads(response.text.encode('utf8'))["error"]["message"])
    self.update_devices(self.args)

