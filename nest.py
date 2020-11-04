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
    #self.listen_event(self.events)
    
  def events(self,event_name,data, kwargs):
    if "climate" in data["entity_id"]:
      self.log(event_name)
      self.log(data)
  
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
    device["attributes"]["friendly_name"]=nest_device["parentRelations"][0]["displayName"] + " Nest Thermostat".replace("'", "")
    device["nest_id"] = nest_device["name"]
    device["attributes"]["entity_id"]="climate." + device["attributes"]["friendly_name"].lower().replace(" ", "_").replace("-", "_")
    device["attributes"]["unit_of_measure"]=nest_device["traits"]["sdm.devices.traits.Settings"]["temperatureScale"].lower()
    if device["attributes"]["unit_of_measure"] == "fahrenheit":
      device["attributes"]["min_temp"]=55
      device["attributes"]["max_temp"]=95
      device["attributes"]["unit_of_measure"] = u"\N{DEGREE SIGN}"+"F"
    else:
      device["attributes"]["min_temp"]=12
      device["attributes"]["max_temp"]=35
      device["attributes"]["unit_of_measure"] = u"\N{DEGREE SIGN}"+"C"
    device["attributes"]["precision"]=0.1
    device["attributes"]["hvac_mode"]=nest_device["traits"]["sdm.devices.traits.ThermostatMode"]["mode"].lower().replace("heatcool", "heat_cool")
    device["attributes"]["fan_mode"]=nest_device["traits"]["sdm.devices.traits.Fan"]["timerMode"].lower()
    if device["attributes"]["fan_mode"] == "on":
      device["attributes"]["fan_timer_out"]=nest_device["traits"]["sdm.devices.traits.Fan"]["timerTimeout"].lower()
    else:
      device["attributes"]["fan_timer_out"]="off"
    if nest_device["traits"]["sdm.devices.traits.ThermostatEco"]["mode"] == "MANUAL_ECO":
      device["attributes"]["preset_mode"]="eco"
    else:
      device["attributes"]["preset_mode"]=""
    #device["attributes"]["eco_min_temp"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatEco"]["heatCelsius"], device["attributes"]["unit_of_measure"])
    #device["attributes"]["eco_max_temp"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatEco"]["coolCelsius"], device["attributes"]["unit_of_measure"])
    device["attributes"]["hvac_modes"]=nest_device["traits"]["sdm.devices.traits.ThermostatMode"]["availableModes"]
    device["attributes"]["hvac_modes"]=[mode.lower().replace("heatcool", "heat_cool") for mode in device["attributes"]["hvac_modes"]]
    device["attributes"]["preset_modes"]=["eco"]
    device["attributes"]["current_temperature"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.Temperature"]["ambientTemperatureCelsius"], device["attributes"]["unit_of_measure"])
    device["attributes"]["current_humidty"]=nest_device["traits"]["sdm.devices.traits.Humidity"]["ambientHumidityPercent"]
    device["attributes"]["hvac_action"]=nest_device["traits"]["sdm.devices.traits.ThermostatHvac"]["status"].lower()
    device["attributes"]["supported_features"]=25
    if device["attributes"]["hvac_action"] == "off":
      device["attributes"]["hvac_action"]="idle"
    if "heat_cool" in device["attributes"]["hvac_modes"]:
      device["attributes"]["supported_features"]+=2
    if device["attributes"]["preset_mode"]=="eco":
      device["state"]="on"
      device["attributes"]["target_temp_low"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatEco"]["heatCelsius"], device["attributes"]["unit_of_measure"])
      device["attributes"]["target_temp_high"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatEco"]["coolCelsius"], device["attributes"]["unit_of_measure"])
    elif device["attributes"]["hvac_mode"] == "heat":
      device["state"]="on"
      device["attributes"]["temperature"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["heatCelsius"], device["attributes"]["unit_of_measure"])
    elif device["attributes"]["hvac_mode"] == "cool":
      device["state"]="on"
      device["attributes"]["temperature"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["coolCelsius"], device["attributes"]["unit_of_measure"])
    elif device["attributes"]["hvac_mode"] == "heat_cool":
      device["state"]="on"
      device["attributes"]["target_temp_low"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["heatCelsius"], device["attributes"]["unit_of_measure"])
      device["attributes"]["target_temp_high"]=self.convert_temp_up(nest_device["traits"]["sdm.devices.traits.ThermostatTemperatureSetpoint"]["coolCelsius"], device["attributes"]["unit_of_measure"])
    else:
      device["state"]="off"
    return device
  
  def convert_temp_up(self, temp, unit_of_measure):
    value=0.0
    if unit_of_measure == u"\N{DEGREE SIGN}"+"F":
      value=round(temp*9/5+32, 1)
    else:
      value=round(temp, 1)
    return value
    
  def convert_temp_down(self, temp, unit_of_measure):
    value=0.0
    if unit_of_measure == u"\N{DEGREE SIGN}"+"F":
      value=round((temp-32)*5/9, 1)
    else:
      value=round(temp, 1)
    return value
  
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
    elif data["service"]=="set_fan_mode":
      self.set_fan_mode(data)
    elif data["service"]=="set_preset_mode":
      self.set_preset_mode(data)
  
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
  
  def set_preset_mode(self, data):
    self.log("set_preset_mode")
    id = data["service_data"]["entity_id"]
    payload={}
    if data["service_data"]["preset_mode"].lower() == "eco":
      payload = json.dumps({
        'command' : 'sdm.devices.commands.ThermostatEco.SetMode',
        'params' : {
          'mode' : 'MANUAL_ECO'
          }
        }, indent=4)
    else:
      return
    self.post_api(self.devices[id], payload)
    
  def set_fan_mode(self, data):
    self.log("set_fan_mode")
    id = data["service_data"]["entity_id"]
    payload={}
    if data["service_data"]["fan_mode"].lower() == "off":
      
      payload = json.dumps({
        'command' : 'sdm.devices.commands.Fan.SetTimer',
        'params' : {
          'timerMode' : 'OFF'
          }
        }, indent=4)
    else:
      payload = json.dumps({
        'command' : 'sdm.devices.commands.Fan.SetTimer',
        'params' : {
          'timerMode' : 'ON',
          'duration' : '900s'
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
          "coolCelsius" : self.convert_temp_down(float(data["service_data"]["target_temp_high"]), self.devices[id]["attributes"]["unit_of_measure"]),
          "heatCelsius" : self.convert_temp_down(flaot(data["service_data"]["target_temp_low"]), self.devices[id]["attributes"]["unit_of_measure"])
          }
        }, indent=4)
      self.post_api(self.devices[id], payload)
    elif self.devices[id]["attributes"]["hvac_mode"] == "cool":
      payload = json.dumps({
        "command" : "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
        "params" : {
          "coolCelsius" : self.convert_temp_down(float(data["service_data"]["temperature"]), self.devices[id]["attributes"]["unit_of_measure"])
          }
        }, indent=4)
      self.post_api(self.devices[id], payload)
    elif self.devices[id]["attributes"]["hvac_mode"] == "heat":
      payload = json.dumps({
        "command" : "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
        "params" : {
          "heatCelsius" : self.convert_temp_down(float(data["service_data"]["temperature"]), self.devices[id]["attributes"]["unit_of_measure"])
          }
        }, indent=4)
      self.post_api(self.devices[id], payload)

  
  def post_api(self, device, payload):
    if payload == {}:
      return
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

