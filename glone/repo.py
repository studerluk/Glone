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


class GitRepo(object):
	def __init__(self, repo_config):
		norm_repo = Validator(repo_schema).normalized({})
		self.__dict__.update(**norm_repo)

		for key, value in norm_repo.items():
			if key in repo_config and repo_config[key] != value:
				del repo_config[key]

		self.__dict__.update(**repo_config)

		if 'name' not in repo_config:
			self.name = self.id
