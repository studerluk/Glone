#/usr/bin/python3


import os, sys
import re
import logging

from pathlib import Path
from copy import deepcopy

import gitlab

from cerberus import Validator

from glone import schema
from glone.group import GloneGroup
from glone.repo import GloneRepo


logging.basicConfig(format='%(levelname)-10s ->\t%(message)s', level=logging.INFO)


class GloneRemote(object):
	def __init__(self, auth, remote_config, default_config):
		self._auth = auth

		norm_remote = Validator(schema.remote).normalized({})
		self.__dict__.update(**norm_remote)

		defaults = deepcopy(default_config)
		self.__dict__.update(**(defaults['defaults']['remotes']))
		del defaults['defaults']['remotes']
		self.__dict__.update(**defaults)

		if remote_config['defaults'] == {}:
			del remote_config['defaults']

		if remote_config['discovery'] == {} or remote_config['discovery'] == False:
			del remote_config['discovery']

		for key, value in norm_remote.items():
			if key in remote_config and remote_config[key] == value:
				del remote_config[key]

		self.__dict__.update(**remote_config)

		if 'name' not in remote_config:
			self.name = self.id

		self._git = self._connect()

		# setup groups
		self.groups = [GloneGroup(group, self.defaults) for group in self.groups]

		self.users = [GloneGroup(user, self.defaults) for user in self.users]


	def _connect(self):
		logging.error("Use of abstract remote not supported")
		sys.exit(1)

		return None


	def get_repo(self, repo):
		pass


	def __str__(self):
		return f"{self.__dict__}"


class GitlabRemote(GloneRemote):
	def __init__(self, auth, emote_config, default_config):
		super().__init__(auth, emote_config, default_config)

		if self.discovery != {} and self.discovery != False:
			git_groups = self._git.groups.list(all=True, owned=self.discovery['owned_only'], starred=self.discovery['starred_only'])
			git_groups = [g for g in git_groups if g.parent_id is None]

			for pattern in self.discovery['excludes']:
				git_groups = list(filter(lambda g: not re.match(pattern, g.name), git_groups))

			for group in git_groups:
				group_config = Validator(schema.group).normalized({})
				group_config['id']      = group.path
				group_config['name']    = group.name
				group_config['source']  = group.path
				group_config['dest']    = group.name.replace(' ', '')

				if not any([g.source == group_config['source'] for g in self.groups]):
					self.groups.append(GloneGroup(group_config, self.defaults))
					logging.info(f"Add group {group.name} by discovery")


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

		for user in self.users:
			logging.debug(f"Getting group {user.name}")
			git_user = self._git.users.list(username=user.source)[0]
			git_repos = git_user.projects.list(all=True)

			for pattern in user.excludes:
				git_repos = list(filter(lambda r: not re.match(pattern, r.name), git_repos))

			for repo in git_repos:
				dest = Path(repo.attributes['path_with_namespace'])

				if user.dest:
					dest = Path(user.dest) / Path(*(dest.parts[1:]))

				repo_config = {
					'id': repo.id,
					'name': repo.name,
					'source': repo.attributes[f"{user.protocol}_url_to_repo"],
					'dest': dest,
					'clone': user.defaults['clone'],
					'tasks': user.defaults['tasks']
				}
				repo_config.update(**user.defaults)

				repos.append(GloneRepo(repo_config))

		for group in self.groups:
			logging.debug(f"Getting group {group.name}")
			git_group = self._git.groups.get(group.source)
			git_repos = git_group.projects.list(all=True, include_subgroups=True)

			for pattern in group.excludes:
				git_repos = list(filter(lambda r: not re.match(pattern, r.name), git_repos))

			for repo in git_repos:
				dest = Path(repo.attributes['path_with_namespace'])

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

				repos.append(GloneRepo(repo_config))

		return repos


class GithubRemote(GloneRemote):
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
