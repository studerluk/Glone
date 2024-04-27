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


class Remote(object):
	def __init__(self, remote_config, default_config):
		norm_remote = Validator(remote_schema).normalized({})
		self.__dict__.update(**norm_remote)

		defaults = deepcopy(default_config)
		self.__dict__.update(**(defaults['defaults']['remotes']))
		del defaults['defaults']['remotes']
		self.__dict__.update(**defaults)

		if remote_config['defaults'] == {}:
			del remote_config['defaults']

		for key, value in norm_remote.items():
			if key in remote_config and remote_config[key] == value:
				del remote_config[key]

		self.__dict__.update(**remote_config)

		if 'name' not in remote_config:
			self.name = self.id

		# connect to remote server
		if self.type == RemoteType.GITLAB.value:
			auth = self.__get_auth(self.auth)
			if auth.get('server', None):
				if auth.get('config', None):
					try:
						self.git = gitlab.Gitlab.from_config(auth['server'], [auth['config']])
					except:
						logging.error(f"Authentication with server '{auth['server']}' and config '{auth['config']}' failed")
						sys.exit(1)
				else:
					try:
						self.git = gitlab.Gitlab.from_config(auth['server'])
					except:
						logging.error(f"Authentication with server '{auth['server']}' failed")
						sys.exit(1)

			elif auth.get('token', None):
				try:
					self.git = gitlab.Gitlab.from_config(url=self.url, private_token=auth['token'])
				except:
					logging.error(f"Authentication with url '{self.url}' and token ailed")
					sys.exit(1)

			else:
				logging.error("Unabel to authenticate")
				sys.exit(1)

		elif self.type == RemoteType.GITHUB.value:
			logging.error("GitHub remotes are not yet supported")
			sys.exit(1)

		else:
			logging.error(f"Unknown remote type: {self.type}")
			sys.exit(1)

		# setup groups
		groups = []
		for group in self.groups:
			groups.append(Group(group, self.defaults))

		self.groups = groups


	def __get_config(self, remote_id):
		remote = [r for r in config['remotes'] if r['id'] == remote_id]

		if len(remote) > 1:
			logging.error(f"Multiple remotes with id '{remote_id}' found")
			sys.exit(1)
		elif len(remote) == 0:
			logging.error(f"No remote found with id '{remote_id}'")
			sys.exit(1)

		return remote[0]


	def __get_auth(self, auth_id):
		auth = [a for a in config['auth'] if a['id'] == auth_id]

		if len(auth) > 1:
			logging.error(f"Multiple auths with id '{auth_id}' found")
			sys.exit(1)
		elif len(auth) == 0:
			logging.error(f"No auth found with id '{auth_id}'")
			sys.exit(1)

		return auth[0]


	def get_repos(self):
		repos = []

		if self.type == RemoteType.GITLAB.value:
			for group in self.groups:
				logging.debug(f"Getting group {group.name}")
				git_group = self.git.groups.get(group.source)
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

		elif self.type == RemoteType.GITHUB.value:
			logging.error("GitHub remotes are not yet supported")
			sys.exit(1)

		else:
			logging.error(f"Unknown remote type: {self.type}")
			sys.exit(1)

		return repos


	def get_repo(self, repo):
		pass


# Arg parsing
def parseArgs():
	parser = argparse.ArgumentParser(description = "Mass manage git repositories across multiple remotes")

	parser.add_argument('-f', '--file',     help='Root directory for git repositories',
		type=str, default='repos.yml',            required=False)

	parser.add_argument('--prefix',         help='Root directory for git repositories',
		type=str, default='./',                   required=False)

	args = parser.parse_args()
	return args


# Functions
def get_remotes(config):
	remotes = []

	for remote in config['remotes']:
		remotes.append(Remote(remote, {'defaults': config.get('defaults', {})}))

	return remotes


def get_repos(config):
	repos = []

	for repo in config.get('repos', []):
		repos.append(GitRepo(repo))

	return repos


def update_repos(repos, config, args):
	output_dir = Path(args.prefix)
	output_dir.mkdir(parents=True, exist_ok=True)

	for repo in repos:
		repo_path = output_dir / repo.dest

		if not os.path.exists(repo_path):
			logging.info(f"git clone {repo.source} {repo_path}")
			Path(repo_path.parent).mkdir(parents=True, exist_ok=True)
			Repo.clone_from(repo.source, repo_path)

		logging.info(f"Running tasks {repo.tasks} on {repo_path}")
		git_repo = Repo(repo_path)
		for task in repo.tasks:
			if not task.startswith("git "):
				task = f"git {task}"
			git_repo.git.execute(task.split(" "))


# Main
if '__name__' != '__main__':
	args = parseArgs()

	with open(args.file) as file:
		config = yaml.safe_load(file)

	validator = Validator(schema)

	if not validator.validate(config):
		logging.error(f"Errors when validating config file '{args.file}'")
		pprint(validator.errors)
		sys.exit(1)

	config = validator.normalized(config)

	remotes = get_remotes(config)

	repos = []
	for remote in remotes:
		repos += remote.get_repos()

	repos += get_repos(config)

	update_repos(repos, config, args)
