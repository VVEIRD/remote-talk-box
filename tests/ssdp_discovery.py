from ssdpy import SSDPClient
client = SSDPClient()
devices = client.m_search("ssdp:all", 2)
for device in devices:
    print(device)
    print(device.get("usn"))