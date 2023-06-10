#!/usr/bin/python3


import os, sys
import gitlab
import shutil
import argparse
from pathlib import Path



def parseArgs():
	parser = argparse.ArgumentParser(description = "Glone")

	parser.add_argument('--outdir',   type=str, default='./',                   required=False)
	parser.add_argument('--server',   type=str, default='github.com',           required=False)

	parser.add_argument('--http',     action='store_true',                      required=False)
	parser.add_argument('--ssh',      action='store_true',                      required=False)

	parser.add_argument('--starred',  action='store_true',                      required=False)

	parser.add_argument('--outfile',  type=str, default='tmp/gitlab-clone.sh',  required=False)

	args = parser.parse_args()

	if args.http and args.ssh:
		raise Exception('Use either https or ssh, not both...')

	return args

if '__name__' != '__main__':
	args = parseArgs()

	git = gitlab.Gitlab.from_config(args.server)

	mkdir_commands = []
	for group in git.groups.list(all=True):
		path = os.path.normpath(f"{args.outdir}/{group.attributes['full_path']}")

		command = f"mkdir -p {path}"
		mkdir_commands.append(command)

	git_commands = []
	for prj in git.projects.list(all=True):
		repo_url = prj.attributes['ssh_url_to_repo']
		if args.http:
			repoUrl = prj.attributes['http_url_to_repo']


		path = os.path.normpath(f"{args.outdir}/{prj.attributes['path_with_namespace']}")

		command = f"git clone {repo_url} {path}"
		git_commands.append(command)

	Path(os.path.dirname(args.outfile)).mkdir(parents=True, exist_ok=True)
	with open(args.outfile, 'w') as f:
		for command in mkdir_commands + git_commands:
			f.write(command)
			f.write('\n')
