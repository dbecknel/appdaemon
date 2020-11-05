# appdaemon

# NESTAPI - nest.py

Google API for NEST Apps for Appdaemon on HASSIO

nest.py is my intial cut at getting my Home Assistant to work with the new Google API for Nest Thermostats.

https://developers.google.com/nest/device-access/registration

You will need to carefully follow the instruction on the above link to register for the API and setup an account in GCP.  Ulimately, you will need the Project ID from you Google Device Access Console and the Client ID, Client Secret, and the Refresh Token from registering your Nest device API with your GCP account.  Again, the link above has good instructions to do, but follow them carefully!!

Best to have Postman downloaded to help and to test fire API calls to be sure your data artifacts are correct.

I am NOT a programmer, but any means.  There are most likely errors and better ways to factor the code and such.  I am open to feedback.  Hopefully, HASS will integrate the Google API for NEST directly in the coming months.  However, efforts thus far are limited to sensors with no control of the actual thermostat.  That will change soon, I know.  I am not one to be known for patience though.

I have included the apps.yaml file which includes the extract needed to run this file.  You will need to update your secrets.yaml file with the appropriate information.

NEST uses celsius under the hood, but has a trait that stipulates if your thermostats are set for Fahrenheit or Celsius.  The script is now aware of that election and computes the correct temperatures for display in HASS.  I originally forced it all to Fahrenheit...

This works for an arbitrary number of thermostats and sets up the devices at runtime.  I fixed the information needed to get the lovelace visualization to set the temperature.  The issue was the need to set a min and max temp that is used by lovelace to setup the input_number.  Services firing manually or from automations have now been tested, or at least most of them.

ECO and fan only are now supported and enabled.  The only preset mode is ECO which relies on the eco temperatures setup in the NEST app.

Happy automating!!

# MerakiAPI - meraki.py

I put this together that I can switch in home assistant to toggle network clients on my Meraki between two group policies.  This is still very much a prototype, but there is not an integration to this API already built, so I figured I would take a whirl.

the group policy ID's are static at this point, but would be trivial to paramterize them if their was any interest.

Switches look like: "switch.meraki_<meraki_client_id>" and the attributes are populated with relatively useful information.  The friendly name uses the information in the client description field and mac address to ensure some level of uniqueness.
