#!/usr/bin/python3


import os, sys
import re
import gitlab
from git import Repo
import shutil
import argparse
from pathlib import Path



def parseArgs():
	parser = argparse.ArgumentParser(description = "Glone")

	parser.add_argument('--outdir',         help='Output directory for cloned repositories',
		type=str, default='./',                   required=False)
	parser.add_argument('--server',         help='Server ID configured in ~/.python-gitlab.cfg',
		type=str, default='gitlab',               required=False)

	parser.add_argument('--uri',            help='Whether to use SSH or HTTP',
		choices=['http', 'ssh'],  default='ssh',  required=False)

	parser.add_argument('--starred',        help='Only clone starred projects (can be combined with --owned)',
		action='store_true',                      required=False)
	parser.add_argument('--owned',          help='Only clone owned projects (can be combined with --starred)',
		action='store_true',                      required=False)

	parser.add_argument('--groups',         help='Comma separated list of top level group names to clone',
		type=str, default='',                     required=False)

	parser.add_argument('-e', '--exclude',  help='Exclude file containing RegEx patterns to exclude (use lowercase, not compatible with include)',
		type=str, default='',                     required=False)

	parser.add_argument('-i', '--include',  help='Include file containing RegEx patterns to include (use lowercase, not compatible with exclude)',
		type=str, default='',                     required=False)


	args = parser.parse_args()
	return args


if '__name__' != '__main__':
	args = parseArgs()

	git = gitlab.Gitlab.from_config(args.server)

	groups = args.groups.split(',')


	projects = git.projects.list(all=True, owned=args.owned, starred=args.starred)
	if args.groups:
		projects = [prj
			for prj in projects
				if any([prj.attributes['path_with_namespace'].startswith(g.strip()) for g in groups])
		]

	if args.include:
		with open(args.include, 'r') as file:
			include_patterns = file.readlines()

		include_patterns = [pattern.strip() for pattern in include_patterns]

		if include_patterns:
			projects = [prj
				for prj in projects
					if any([re.match(rf"{pattern}", prj.attributes['name_with_namespace'].lower().replace(' ', '')) for pattern in include_patterns])
			]

	elif args.exclude:
		with open(args.exclude, 'r') as file:
			exclude_patterns = file.readlines()

		exclude_patterns = [pattern.strip() for pattern in exclude_patterns]

		if exclude_patterns:
			projects = [prj
				for prj in projects
					if not any([re.match(rf"{pattern}", prj.attributes['name_with_namespace'].lower().replace(' ', '')) for pattern in exclude_patterns])
			]

	print("Will download following repositories")
	for prj in projects:
		print(prj.attributes['name_with_namespace'])

	print("---------------------------------------------------------------")
	for prj in projects:
		repo_url = prj.attributes[f"{args.uri}_url_to_repo"]
		repo_path = os.path.normpath(f"{args.outdir}/{prj.attributes['path_with_namespace']}")

		#print(f"mkdir -p {os.path.dirname(repo_path)}")
		if os.path.exists(repo_path):
			print(f"Fetching Repo {repo_path}...", end="")
			repo = Repo(repo_path)
			repo.git.fetch()
			print(" Done")
		else:
			print(f"git clone {repo_url} {repo_path}...", end="")
			Path(os.path.dirname(repo_path)).mkdir(parents=True, exist_ok=True)
			Repo.clone_from(repo_url, repo_path)
			print(" Done")
