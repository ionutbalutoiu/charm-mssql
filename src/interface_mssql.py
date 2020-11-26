#!/usr/bin/env python3

import logging

from ops.framework import Object
from charmhelpers.core import host

from mssql_db_client import MSSQLDatabaseClient
from interface_mssql_peer import MssqlPeer

logger = logging.getLogger(__name__)


class MssqlDBProvides(Object):

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.db_rel_name = relation_name
        self.app = self.model.app
        self.unit = self.model.unit
        self.mssql_peer = MssqlPeer(self, 'peers')
        self.framework.observe(
            charm.on[relation_name].relation_changed,
            self.on_changed)
        self.framework.observe(
            charm.on[relation_name].relation_departed,
            self.on_departed)

    def on_changed(self, event):
        if not self.unit.is_leader():
            logger.warning('Unit is not leader. '
                           'Skipping _db_changed() handler.')
            return

        rel_data = self.db_rel_data(event)
        if not rel_data:
            logging.info("The db relation data is not available yet.")
            return

        logging.info("Handling db request.")

        rel = self.model.get_relation(
            event.relation.name,
            event.relation.id)
        db_host = self.relation_bind_address(rel)
        db_client = self.mssql_db_client(db_host)
        db_user_password = self.handle_db_request(
            rel_data['database'],
            rel_data['username'],
            db_client)

        # advertise on app
        rel.data[self.app]['db_host'] = db_host
        rel.data[self.app]['password'] = db_user_password
        # advertise on unit
        rel.data[self.unit]['db_host'] = db_host
        rel.data[self.unit]['password'] = db_user_password

    def on_departed(self, event):
        if not self.unit.is_leader():
            logger.warning('Unit is not leader. '
                           'Skipping _db_departed() handler.')
            return

        rel_data = self.db_rel_data(event)
        if not rel_data:
            logger.warning('No relation data. '
                           'Skipping _db_departed() handler.')
            return

        rel = self.model.get_relation(
            event.relation.name,
            event.relation.id)
        db_host = self.relation_bind_address(rel)
        db_client = self.mssql_db_client(db_host)
        db_client.revoke_access(
            rel_data['database'], rel_data['username'])

    def db_rel_data(self, event):
        rel_data = event.relation.data.get(event.unit)
        if not rel_data:
            return {}

        database = rel_data.get('database')
        username = rel_data.get('username')

        if not database or not username:
            return {}

        return {
            'database': database,
            'username': username,
        }

    def handle_db_request(self, db_name, db_user_name, db_client):
        db_user_pass = host.pwgen(32)

        db_client.create_database(db_name)
        db_client.create_login(db_user_name, db_user_pass)
        db_client.grant_access(db_name, db_user_name)

        return db_user_pass

    def relation_bind_address(self, relation):
        return str(self.model.get_binding(relation).network.bind_address)

    def mssql_db_client(self, db_host):
        return MSSQLDatabaseClient(
            user='SA',
            password=self.mssql_peer.get_peers_rel_data('sa_password'),
            host=db_host)
