# Glone

Download all your projects from GitLab maintaining repo structure

## Requirements
```
apt install \
	python3 \
	pyhton3-pip

pip3 install -r requirements.txt
```

## Quick Start
```
[global]
default = my-server
ssl_verify = true
timeout = 60

[my-server]
url = <base-url>
private_token = <token>
api_version = 4
```

```
./glone.py -f <config.yml> [--prefix <prefix>]
```
