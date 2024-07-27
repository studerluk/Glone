#/usr/bin/python3


import os, sys
import argparse
import yaml
import logging

from pathlib import Path

from git import Repo

from cerberus import Validator

from pprint import pprint
from tabulate import tabulate

from glone import schema
from glone import GithubRemote, GitlabRemote
from glone import GloneGroup
from glone import GloneRepo



logging.basicConfig(format='%(levelname)-10s -> %(message)s', level=logging.INFO)

DEFAULT_GLONE_FILE    = 'glone.yml'
DEFAULT_GLONE_PREFIX  = './repos'


# Arg parsing
def parseArgs():
	parser = argparse.ArgumentParser(description = "Mass manage git repositories across multiple remotes")

	parser.add_argument('-f', '--file',     help='Config file containing repo list',
		type=str, default=DEFAULT_GLONE_FILE,    required=False)

	parser.add_argument('--prefix',         help='Root directory for git repositories to be cloned into',
		type=str, default=DEFAULT_GLONE_PREFIX,  required=False)

	subparsers = parser.add_subparsers(dest='command', help='')

	parser_diff = subparsers.add_parser('diff', help='Show diff between local and remote')
	parser_diff.add_argument('--format',  type=str,  default='github', help='Output format (supports \'tabulate\' formats)')
	parser_diff.add_argument('--git',     action='store_true',         help='Show diff of git repo (git status --porcelain)')
	parser_diff.add_argument('--path',    action='store_true',         help='Show diff of repo location')
	parser_diff.add_argument('--all',     action='store_true',         help='Show all diff options')
	parser_diff.set_defaults(func=diff_repos)

	parser_update = subparsers.add_parser('update', help='Update local or remote state')
	update_group = parser_update.add_mutually_exclusive_group(required=False)
	update_group.add_argument('--local',   action='store_true',  help='Update local state from remote')
	update_group.add_argument('--remote',  action='store_true',  help='Update remote state from local')
	parser_update.set_defaults(func=update_repos)

	parser_list = subparsers.add_parser('list', help='List known repos')
	list_group = parser_list.add_mutually_exclusive_group(required=False)
	list_group.add_argument('--local',    action='store_true',          help='List local repos')
	list_group.add_argument('--remote',   action='store_true',          help='List remote repos')
	parser_list.add_argument('--format',  type=str,  default='github',  help='Output format (supports \'tabulate\' formats)')
	parser_list.set_defaults(func=list_repos)

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


def get_local_repos(prefix):
	start_path = Path(prefix)
	git_dirs = [str(p) for p in start_path.rglob('.git') if p.is_dir()]
	return git_dirs


def update_repos(repos, config, args):
	output_dir = Path(args.prefix)
	output_dir.mkdir(parents=True, exist_ok=True)

	if args.remote:
		pass

	else: # local (default)
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


def diff_repos(repos, config, args):
	git_dirs = get_local_repos(args.prefix)
	local_only = [git_dir for git_dir in git_dirs]


	if args.path or args.all:
		# Both but different paths
		data = []
		header = ["Name", "Remote", "Local Dest", "Config Dest"]
		data = [header]

		for repo in repos:
			found = False
			for git_dir in local_only:
				remotes = [remote.url for remote in Repo(git_dir).remotes]
				if repo.source in remotes:
					found = True
					if (Path(args.prefix) / repo.dest != Path(git_dir).parent):
						row = [
							repo.name,
							repo.source,
							Path(git_dir).parent,
							Path(args.prefix) / repo.dest
						]
						data.append(row)

			if not found:
				row = [
					repo.name,
					repo.source,
					"-",
					Path(args.prefix) / repo.dest
				]
				data.append(row)

		for git_dir in local_only:
			remotes = [remote.url for remote in Repo(git_dir).remotes]
			found = False
			for repo in repos:
				if repo.source in remotes:
					found = True

			if not found:
				row = [
					Path(git_dir).parent.name,
					remotes[0] if len(remotes) > 0 else "-",
					Path(git_dir).parent,
					"-"
				]
				data.append(row)


		print("# Repos with unexpected location")
		print("")
		print(tabulate(data, headers="firstrow", tablefmt=args.format))
		print("\n")


	if args.git or args.all:
		# Git status
		data = []
		header = ["Name", "Path", "Status", "Branches"]
		data = [header]

		for git_dir in local_only:
			repo = Repo(git_dir)
			diffs = repo.git.status('--porcelain').split('\n')
			branches = repo.branches
			active_branch = repo.active_branch

			branch_list = []
			for branch in branches:
				pref = '*' if branch.name == active_branch.name else "-"
				tracking_branch = branch.tracking_branch()
				if tracking_branch:
					branch_diff = repo.git.rev_list('--left-right', '--count', f'{tracking_branch.name}...{branch.name}').split()
					branch_list.append(f"{pref} {branch.name} [{tracking_branch.name} v{branch_diff[0]} / ^{branch_diff[1]}]")
				else:
					branch_list.append(f"{pref} {branch.name} []")

			for i in range(max(len(diffs), len(branch_list), 1)):
				row = [
					Path(git_dir).parent.name if i == 0 else "",
					Path(git_dir).parent if i == 0 else "",
					diffs[i] if i < len(diffs) else "",
					branch_list[i] if i < len(branch_list) else ""
				]
				data.append(row)

		print("# Repos status")
		print("")
		print(tabulate(data, headers="firstrow", tablefmt=args.format))
		print("\n")


def list_repos(repos, config, args):
	data = []

	if args.local:
		git_dirs = get_local_repos(args.prefix)

		header = ["Name", "Path", "Remote"]
		data = [header]

		for git_dir in git_dirs:
			row = [
				Path(git_dir).parent.name,
				Path(git_dir).parent,
				[f"{remote.name}: {remote.url}" for remote in Repo(git_dir).remotes]
			]
			data.append(row)

	else: # remote (default)
		header = ["Name", "Source", "Dest"]

		data = [header]
		for repo in repos:
			row = [
				repo.name,
				repo.source,
				Path(args.prefix) / repo.dest
			]
			data.append(row)

	print(tabulate(data, headers="firstrow", tablefmt=args.format))
	print("")


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

	if args.command:
		args.func(repos, config, args)
	else:
		logging.error("No or unkown subcommand... Use --help for more info on usage")
