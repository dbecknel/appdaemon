# appdaemon
Google API for NEST Apps for Appdaemon on HASSIO

nest.py is my intial cut at getting my Home Assistant to work with the new Google API for Nest Thermostats.

https://developers.google.com/nest/device-access/registration

You will need to carefully follow the instruction on the above link to register for the API and setup an account in GCP.  Ulimately, you will need the Project ID from you Google Device Access Console and the Client ID, Client Secret, and the Refresh Token from registering your Nest device API with your GCP account.  Again, the link above has good instructions to do, but follow them carefully!!

Best to have Postman downloaded to help and to test fire API calls to be sure your data artifacts are correct.

I am NOT a programmer, but any means.  There are most likely errors and better ways to factor the code and such.  I am open to feedback.  Hopefully, HASS will integrate the Google API for NEST directly in the coming months.

I have included the apps.yaml file which includes the extract needed to run this file.  You will need to update your secrets.yaml file with the appropriate information.

This works for an arbitrary number of thermostats and sets up the devices at runtime.  I couldn't manage to get the lovelace visualization to set the temperature.  I imagine there to be some magic under the hood of the climate class that I can't access from appdaemon.  Services firing manually or from automations should work though.

I didn't bother with Presets or ECO, but would be easy enough to add.

Happy automating!!
