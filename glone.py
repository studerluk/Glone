#/usr/bin/python3


import os, sys
import argparse
import yaml
import logging

from pathlib import Path

from git import Repo

from cerberus import Validator

from pprint import pprint

from glone import schema
from glone import GithubRemote, GitlabRemote
from glone import GloneGroup
from glone import GloneRepo



logging.basicConfig(format='%(levelname)-10s -> %(message)s', level=logging.INFO)


# Arg parsing
def parseArgs():
	parser = argparse.ArgumentParser(description = "Mass manage git repositories across multiple remotes")

	parser.add_argument('-f', '--file',     help='Root directory for git repositories',
		type=str, default='repos.yml',            required=False)

	parser.add_argument('--prefix',         help='Root directory for git repositories',
		type=str, default='./',                   required=False)

	args = parser.parse_args()
	return args


def get_auth(config, auth_id):
	auth = [a for a in config['auth'] if a['id'] == auth_id]

	if len(auth) > 1:
		logging.error(f"Multiple auths with id '{auth_id}' found")
		sys.exit(1)

	elif len(auth) == 0:
		logging.error(f"No auth found with id '{auth_id}'")
		sys.exit(1)

	return auth[0]


# Functions
def get_remotes(config):
	remotes = []

	for remote in config['remotes']:
		auth = get_auth(config, remote['auth'])

		if remote['type'] == schema.RemoteType.GITLAB.value:
			remotes.append(GitlabRemote(auth, remote, {'defaults': config.get('defaults', {})}))

		elif remote['type'] == schema.RemoteType.GITHUB.value:
			remotes.append(GithubRemote(auth, remote, {'defaults': config.get('defaults', {})}))

		else:
			logging.error(f"Unknown remote type '{config['type']}'")
			sys.exit(1)

	return remotes


def get_repos(config):
	repos = []

	for repo in config.get('repos', []):
		repos.append(GloneRepo(repo))

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

	validator = Validator(schema.config)

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
