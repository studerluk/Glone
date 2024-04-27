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
from glone.group import Group
from glone.repo import GitRepo


logging.basicConfig(format='%(levelname)-10s -> %(message)s', level=logging.INFO)


class Remote(object):
	def __init__(self, auth, remote_config, default_config):
		self._auth = auth

		norm_remote = Validator(remote_schema).normalized({})
		self.__dict__.update(**norm_remote)

		defaults = deepcopy(default_config)
		self.__dict__.update(**(defaults['defaults']['remotes']))
		del defaults['defaults']['remotes']
		self.__dict__.update(**defaults)

		if remote_config['defaults'] == {}:
			del remote_config['defaults']

		if remote_config['discovery'] == {}:
			del remote_config['discovery']

		for key, value in norm_remote.items():
			if key in remote_config and remote_config[key] == value:
				del remote_config[key]

		self.__dict__.update(**remote_config)

		if 'name' not in remote_config:
			self.name = self.id

		self._git = self._connect()

		# setup groups
		groups = []
		for group in self.groups:
			groups.append(Group(group, self.defaults))

		self.groups = groups


	def _connect(self):
		logging.error("Use of abstract remote not supported")
		sys.exit(1)

		return None


	def get_repo(self, repo):
		pass


class GitlabRemote(Remote):
	def __init__(self, auth, emote_config, default_config):
		super().__init__(auth, emote_config, default_config)


	def _connect(self):
		git = None

		if self._auth.get('server', None):
			if self._auth.get('config', None):
				try:
					git = gitlab.Gitlab.from_config(self._auth['server'], [self._auth['config']])
				except:
					logging.error(f"Authentication with server '{self._auth['server']}' and config '{self._auth['config']}' failed")
					sys.exit(1)
			else:
				try:
					git = gitlab.Gitlab.from_config(self._auth['server'])
				except:
					logging.error(f"Authentication with server '{self._auth['server']}' failed")
					sys.exit(1)

		elif self._auth.get('token', None):
			try:
				git = gitlab.Gitlab.from_config(url=self.url, private_token=auth['token'])
			except:
				logging.error(f"Authentication with url '{self.url}' and token ailed")
				sys.exit(1)

		else:
			logging.error("Unabel to authenticate")
			sys.exit(1)

		return git


	def get_repos(self):
		repos = []

		git_groups = self._git.groups.list(all=True, owned=self.discovery['owned_only'], starred=self.discovery['starred_only'])
		git_groups = [g for g in git_groups if g.parent_id is None]
		for pattern in self.discovery['excludes']:
			git_groups = list(filter(lambda g: re.match(pattern, g.name), git_groups))

		for group in git_groups:
			group_config = Validator(group_schema).normalized({})
			group_config['id']      = group.path
			group_config['name']    = group.name
			group_config['source']  = group.path
			group_config['dest']    = group.name.replace(' ', '')

			if not any([g.source == group_config['source'] for g in self.groups]):
				self.groups.append(Group(group_config, self.defaults))
				logging.info(f"Add group {group.name} by discovery")

		for group in self.groups:
			logging.debug(f"Getting group {group.name}")
			git_group = self._git.groups.get(group.source)
			git_repos = git_group.projects.list(all=True)

			for pattern in group.excludes:
				git_repos = list(filter(lambda r: re.match(pattern, r.name), git_repos))

			for repo in git_repos:
				dest = Path(repo.attributes['name_with_namespace'].replace(' ', ''))

				if group.dest:
					dest = Path(group.dest) / Path(*(dest.parts[1:]))

				repo_config = {
					'id': repo.id,
					'name': repo.name,
					'source': repo.attributes[f"{group.protocol}_url_to_repo"],
					'dest': dest,
					'clone': group.defaults['clone'],
					'tasks': group.defaults['tasks']
				}
				repo_config.update(**group.defaults)

				repos.append(GitRepo(repo_config))

		return repos


class GithubRemote(Remote):
	def __init__(self, auth, emote_config, default_config):
		super().__init__(auth, emote_config, default_config)


	def _connect(self):
		logging.error("GitHub remotes are not yet supported")
		sys.exit(1)

		return None


	def get_repos(self):
		logging.error("GitHub remotes are not yet supported")
		sys.exit(1)

		return None
