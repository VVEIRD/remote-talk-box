# Remote Box
A Python App that allows for three things:

1. A mumble client that can be told to connect to a server by calling an URL
2. Playing animations on BlinkStick LED devices, also remote activated.
3. Playing wav audio files, also remote activated

The webservice for controlling these can be discovverd via ssdp by searching for the device type "remote-box-client"

There are several URLs that can controll the service, if the service would run on the ip 192.168.1.10:

## Audio
### Status
    http://192.168.1.10:5020/rt-box/audio
Returns a json object with the current status of the audio playback service:

    {
        "audio": {
            "audio_files": [
                "ghost-whispering"
            ],
            "status": {
                "currently_playing": null,
                "queue": [],
                "queue_count": 0
            }
        }
    }

### Playback
    http://192.168.1.10:5020/rt-box/audio/play/ghost-whispering
This will queue the audio file ghost-whisper, which corresponds to the wav file in data/audio/ghost-whisper.wav

It will return the following json:

    {
        "audio": {
            "audio_files": [
                "ghost-whispering"
            ],
            "status": {
                "currently_playing": "ghost-whispering",
                "queue": [],
                "queue_count": 0
            }
        },
        "status": "Audio queued"
    }


### Stop
    http://192.168.1.10:5020/rt-box/audio/stop
This will stop the currently playing file and play the next queued file. It will also return the following json response:

    {
        "audio": {
            "audio_files": [
                "ghost-whispering"
            ],
            "status": {
                "currently_playing": null,
                "queue": [],
                "queue_count": 0
            }
        },
        "status": "Playback stopped"
    }

### Flush Queue
    http://192.168.1.10:5020/rt-box/audio/flush
This will remove any queued files but not stop the currently playing audio. Returns the following json response:

    {
        "audio": {
            "audio_files": [
                "ghost-whispering"
            ],
            "status": {
                "currently_playing": null,
                "queue": [],
                "queue_count": 0
            }
        },
        "status": "Queue flushed"
    }
