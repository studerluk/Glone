#/usr/bin/python3


import os, sys
import re
import argparse
import yaml
import logging

import shutil
from pathlib import Path
from copy import deepcopy

import gitlab
from git import Repo

from cerberus import Validator

from pprint import pprint

from glone.schema import schema, repo_schema, group_schema, remote_schema, GitProtocol, RemoteType



logging.basicConfig(format='%(levelname)-10s -> %(message)s', level=logging.INFO)


class Group(object):
	def __init__(self, group_config, default_config):
		norm_group = Validator(group_schema).normalized({})
		self.__dict__.update(**norm_group)

		self.__dict__.update(default_config['groups'])
		self.__dict__.update(**({'defaults': default_config['repos']}))

		for key, value in norm_group.items():
			if key in group_config and group_config[key] == value:
				del group_config[key]

		self.__dict__.update(**group_config)

		if 'name' not in group_config:
			self.name = self.id

		if 'dest' not in group_config:
			self.dest = self.id
