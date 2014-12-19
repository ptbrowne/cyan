#! /usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json

from pprint import pprint
from etcd import Client as EtcdClient

from ConfigParser import ConfigParser

import retrievers
import re

import inquirer

def lreplace(pattern, sub, string):
    """
    Replaces 'pattern' in 'string' with 'sub' if 'pattern' starts 'string'.
    """
    return re.sub('^%s' % pattern, sub, string)

def format_backend_info(info):
    return 'addr %s' % info['addr']

def format_etcd_info(info):
    return 'addr %s, weight %i' % (info['addr'], info['weight'])

class Cyan(object):
    def __init__(self):
        pass

    def setup(self, app, config):
        self.app = app
        self.config = config
        if app:
            self.update()

    def update(self):
        self.etcd_prefix = self.get_config('etcd_prefix')
        self.setup_etcd()
        self.retrieve_backends()
        self.retrieve_etcd()

    def get_config(self, k):
        return self.config.get(self.app, k)

    def retrieve_backends(self):
        retriever_config = self.get_config('retriever').split(' ')
        strategy = retriever_config[0]
        strategy_func = getattr(__import__('retrievers.%s' % strategy), strategy)
        args = retriever_config[1:]
        self.backends = strategy_func.ls(*args)

    def retrieve_etcd(self):
        upstream_prefix = self.etcd_prefix + 'upstream'
        try:
            tree = etcd.read(upstream_prefix, recursive=True, sorted=True)
            self.etcd_backends = {
                lreplace(upstream_prefix + '/', '', child.key) : json.loads(child.value)
                for child in tree.children
            }
        except KeyError:
            self.setup_etcd()
            self.etcd_backends ={}


    def setup_etcd(self):
        haproxy_options = {
            "cookie": self.get_config('haproxy_cookie'),
            "frontend_port": self.get_config('haproxy_frontend_port'),
            "balance": self.get_config('haproxy_balance')
        }
        etcd.set(self.etcd_prefix + '/haproxy_options', json.dumps(haproxy_options))


    def etcd_key(self, backend_name):
        return '%s/upstream/%s' % (self.etcd_prefix, backend_name)


    def set_settings(self, backend_name, options):
        info = self.get_backend_info(backend_name)
        key = self.etcd_key(backend_name)
        settings = dict(info, **options)
        etcd.set(key, json.dumps(settings))

    def add(self, backend_name):
        self.set_settings(backend_name, { 'weight': 0 })
        print (
            '%s added to load-balancer'
            'Initial weight at 0'
            'To force server selection, you should copy this in your browser'
            'document.cookie = "%s=%s"' % (backend_name, self.get_config('haproxy_cookie'), backend_name)
        )
        self.ls()

    def modify(self, backend_name, weight):
        self.set_settings(backend_name, { 'weight': float(weight) })
        print ('%s weight set to %s\n' % (backend_name, weight))
        self.ls()

    def get_backend_info(self, backend_name):
        self.update()
        return self.backends[backend_name]

    def remove(self, backend_name):
        self.update()
        etcd_key =  self.etcd_key(backend_name)
        key = lreplace(self.etcd_prefix + '/upstream/', '', etcd_key)
        if key in self.etcd_backends:
            if len(self.backends.keys()) < 2:
                print 'cannot remove last backend'
            else:
                etcd.delete(etcd_key)
                print '%s removed from load balancer' % (backend_name)
            print
            self.ls()
        else:
            print 'not in load balancer'

    def ls(self):
        if self.app is None:
            print '\n'.join(self.get_apps())
            return
        self.update()
        print 'backends'
        for name, info in self.backends.iteritems():
            status = name in self.etcd_backends
            print '✓' if status else '✗',
            print ('%s' % name).ljust(20),
            if not status:
                print format_backend_info(info)
            else:
                print format_etcd_info(self.etcd_backends[name])
        orphans = [name for name in self.etcd_backends if name not in self.backends]
        if orphans:
            print '\norphans'
            for o in orphans:
                print o

    def add_remove(self):
        backends = self.backends.keys()
        activated_backends = self.etcd_backends.keys()
        self.ls()
        questions = [
            inquirer.Checkbox('activate_backends',
                              message="Activate or deactivate backends ?",
                              choices=backends,
                              default=activated_backends
                              ),
        ]
        answers = inquirer.prompt(questions)
        to_activate = set(answers['activate_backends']) - set(activated_backends)
        to_deactivate = set(backends) - set(answers['activate_backends'])
        if len(to_activate):
            for backend in to_activate:
                self.add(backend)
        if len(to_deactivate):
            for backend in to_deactivate:
                self.remove(backend)
        if len(to_activate):
            self.interactive()

    def modify_weights(self):
        goout = False
        while not goout:
            self.update()
            questions = [
                inquirer.List('backend',
                                  message="Which backend ?",
                                  choices=self.backends.keys() + ['exit']
                                  ),
            ]
            answers = inquirer.prompt(questions)
            if answers['backend'] == 'exit':
                goout = True
                continue
            else:
                backend_info = self.etcd_backends.get(answers['backend'])
                answer = inquirer.prompt([
                    inquirer.Text('weight',
                        message=
                        "Weight ? (previous: %s)" % ( (backend_info or {}).get('weight', 'not active')),
                        validate=lambda _, x: re.match('\d+', x),
                    )
                ])
                self.modify(answers['backend'], answer['weight'])
                print

    def get_apps(self):
        return [c for c in self.config.sections() if c != 'main']

    def interactive(self):
        if not self.app:
            answer = inquirer.prompt([
                inquirer.List('app',
                              message='which app ?',
                              choices=self.get_apps())
            ])
            self.app = answer['app']
            self.update()
        questions = [
            inquirer.List('sub_prompt',
                              message="What do you want to do ?",
                              choices=['modify weights', 'add/remove', 'get_cookie'],
                              ),
        ]
        answers = inquirer.prompt(questions)
        if answers['sub_prompt'] == 'add/remove':
            self.add_remove()
        elif answers['sub_prompt'] == 'modify weights':
            self.modify_weights()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='cyan')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_add = subparsers.add_parser('add', help='Advertise a container to load balancing. Initial weight is 0')
    parser_modify = subparsers.add_parser('modify', help='Modify weight of a container')
    parser_remove = subparsers.add_parser('rm', help='Remove a container from load balancing')
    parser_ls = subparsers.add_parser('ls', help='List')
    parser_interactive = subparsers.add_parser('interactive', help='List')

    cyan = Cyan()
    parser_add.add_argument('app')
    parser_add.add_argument('backend_name')
    parser_add.set_defaults(func=cyan.add)

    parser_modify.add_argument('app')
    parser_modify.add_argument('backend_name')
    parser_modify.add_argument('weight')
    parser_modify.set_defaults(func=cyan.modify)

    parser_remove.add_argument('app')
    parser_remove.add_argument('backend_name')
    parser_remove.set_defaults(func=cyan.remove)

    parser_ls.add_argument('app', nargs='?')
    parser_ls.set_defaults(func=cyan.ls)

    parser_interactive.set_defaults(func=cyan.interactive)
    parser_interactive.add_argument('app', nargs='?')

    args = parser.parse_args()
    config = ConfigParser()
    config.read(['cyan.default.cfg', 'cyan.cfg'])

    etcd_host, etcd_port = config.get('main', 'etcd_server').split(':')
    etcd = EtcdClient(host=etcd_host, port=int(etcd_port))

    cyan.setup(args.app, config)
    remove_args = ['func', 'app']
    rargs = dict( (k,v) for (k,v) in vars(args).iteritems() if k not in remove_args)
    args.func(**rargs)