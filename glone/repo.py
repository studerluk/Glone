#/usr/bin/python3


import os, sys
import re
import logging

from cerberus import Validator

from glone import schema



logging.basicConfig(format='%(levelname)-10s ->\t%(message)s', level=logging.INFO)


class GloneRepo(object):
	def __init__(self, repo_config):
		norm_repo = Validator(schema.repo).normalized({})
		self.__dict__.update(**norm_repo)

		for key, value in norm_repo.items():
			if key in repo_config and repo_config[key] != value:
				del repo_config[key]

		self.__dict__.update(**repo_config)

		if 'name' not in repo_config:
			self.name = self.id


	def __str__(self):
		return f"{self.__dict__}"
