# Schema definition for Glone config

from enum import Enum


# Enums
class RemoteType(Enum):
	GITLAB = 'gitlab'
	GITHUB = 'github'

	@classmethod
	def values(cls):
		return [member.value for member in cls]


class GitProtocol(Enum):
	SSH = 'ssh'
	HTTPS = 'https'

	@classmethod
	def values(cls):
		return [member.value for member in cls]


# Schema definition
__remote_defaults = {
	'auth':      {'type': 'string',  'required': False},
	'type':      {'type': 'string',  'required': False, 'allowed': RemoteType.values()},
	'discovery': {
		'type': 'dict',
		'required': False,
		'schema': {
			'starred_only':  {'type': 'boolean', 'required': False},
			'owned_only':    {'type': 'boolean', 'required': False},
			'excludes':      {'type': 'list',    'required': False, 'schema': {'type': 'string'}, 'default': []},
		},
	},
}

__groups_defaults = {
	'excludes':  {'type': 'list',   'required': False, 'schema': {'type': 'string'}},
	'protocol':  {'type': 'string', 'required': False, 'allowed': GitProtocol.values()},
}

__repos_defaults = {
	'clone':     {'type': 'boolean', 'required': False},
	'tasks':     {'type': 'list',    'required': False, 'schema': {'type': 'string'}},
}

__auth_schema = {
	'id':      {'type': 'string', 'required': True},
	'name':    {'type': 'string', 'required': False},
	'server':  {'type': 'string', 'required': False},
	'user':    {'type': 'string', 'required': False},
	'token':   {'type': 'string', 'required': False},
	'config':  {'type': 'string', 'required': False},
}

group = {
	'id':       {'type': 'string', 'required': True},
	'name':     {'type': 'string', 'required': False},
	'source':   {'type': 'string', 'required': True},
	'dest':     {'type': 'string', 'required': False},
	'protocol': {'type': 'string', 'required': False, 'allowed': GitProtocol.values(), 'default': 'ssh'},
	'excludes': {'type': 'list',   'required': False, 'schema': {'type': 'string'}, 'default': []},
	'defaults': {
		'type': 'dict',
		'required': False,
		'schema': __repos_defaults,
		'default': {}
	}
}

remote = {
	'id':        {'type': 'string',  'required': True},
	'name':      {'type': 'string',  'required': False},
	'url':       {'type': 'string',  'required': False},
	'auth':      {'type': 'string',  'required': False},
	'type':      {'type': 'string',  'required': True, 'allowed': RemoteType.values()},
	'discovery': {
		'type': 'dict',
		'required': False,
		'schema': {
			'starred_only':  {'type': 'boolean', 'required': False, 'default': False},
			'owned_only':    {'type': 'boolean', 'required': False, 'default': False},
			'excludes':      {'type': 'list',    'required': False, 'schema': {'type': 'string'}, 'default': []},
		},
		'default': {}
	},
	'defaults': {
		'type': 'dict',
		'required': False,
		'schema': {
			'groups': {
				'type': 'dict',
				'required': False,
				'schema': __groups_defaults,
				'default': {}
			},
			'repos': {
				'type': 'dict',
				'required': False,
				'schema': __repos_defaults,
				'default': {}
			},
		},
		'default': {}
	},
	'groups': {
		'type': 'list',
		'required': False,
		'schema': {
			'type': 'dict',
			'required': False,
			'schema': group
		}
	},
	'users': {
		'type': 'list',
		'required': False,
		'schema': {
			'type': 'dict',
			'required': False,
			'schema': group
		}
	}
}

repo = {
	'id':      {'type': 'string',  'required': True},
	'name':    {'type': 'string',  'required': False},
	'source':  {'type': 'string',  'required': True},
	'dest':    {'type': 'string',  'required': False},
	'clone':   {'type': 'boolean', 'required': False, 'default': True},
	'tasks':   {'type': 'list',    'required': False, 'schema': {'type': 'string'}, 'default': ["fetch"]},
}


# This is the complete schema
config = {
	'defaults': {
		'type': 'dict',
		'required': False,
		'schema': {
			'remotes': {
				'type': 'dict',
				'required': False,
				'schema': __remote_defaults,
				'default': {}
			},
			'groups': {
				'type': 'dict',
				'required': False,
				'schema': __groups_defaults,
				'default': {}
			},
			'repos': {
				'type': 'dict',
				'required': False,
				'schema': __repos_defaults,
				'default': {}
			}
		},
		'default': {}
	},

	'auth': {
		'type': 'list',
		'required': False,
		'schema': {
			'type': 'dict',
			'required': False,
			'schema': __auth_schema
		}
	},

	'remotes': {
		'type': 'list',
		'required': False,
		'dependencies': 'auth',
		'schema': {
			'type': 'dict',
			'required': False,
			'schema': remote
		}
	},

	'repos': {
		'type': 'list',
		'required': False,
		'schema': {
			'type': 'dict',
			'required': False,
			'schema': repo
		}
	}
}
