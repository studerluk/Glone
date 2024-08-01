#/usr/bin/python3


import os, sys
import re
import logging

from cerberus import Validator

from glone import schema



logging.basicConfig(format='%(levelname)-10s ->\t%(message)s', level=logging.INFO)


class GloneGroup(object):
	def __init__(self, group_config, default_config):
		norm_group = Validator(schema.group).normalized({})
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


	def __str__(self):
		return f"{self.__dict__}"
