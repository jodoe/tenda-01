# Tenda O1 v1 - 500m Outdoor Point To Point CPE 

 ![Tenda O1 ](https://github.com/jodoe/tenda-01/blob/main/O1(3).png)

This is a script to poll the Tenda for live RSSI data, once a second, to help with alignment. The polling happens over TELNET, using a widely published and insecure root password used for other Tenda devices.

To ensure the RSSI is constantly updated, have a ping running to the device in a separate window. If no traffic travels over the link the RSSI information rarely updates on the AP. 

When running, you can view the signal quality RSSI, H and V alignment, Noise, TX speeds and a rough bar graph showing signal quality. 

All of this code is AI generated and should run on Windows or Linux. 
