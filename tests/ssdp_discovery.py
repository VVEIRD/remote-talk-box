from ssdpy import SSDPClient
client = SSDPClient()
devices = client.m_search("mumble-remote-client")
for device in devices:
    print(device)
    print(device.get("usn"))