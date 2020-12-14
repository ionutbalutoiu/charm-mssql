import unittest

from unittest import mock

from ops.testing import Harness
from ops.charm import CharmBase

from interface_mssql_provider import MssqlDBProvider
from interface_mssql_peer import MssqlPeer


class TestInterfaceMssqlDBProvider(unittest.TestCase):

    def setUp(self):
        self.harness = Harness(CharmBase, meta='''
            name: mssql
            provides:
              db:
                interface: mssql
            peers:
              peers:
                interface: mssql-peer
        ''')
        self.addCleanup(self.harness.cleanup)

    @mock.patch.object(MssqlDBProvider, 'mssql_db_client')
    @mock.patch.object(MssqlDBProvider, 'relation_bind_address')
    @mock.patch('charmhelpers.core.host.pwgen')
    def test_on_changed(self,
                        _pwgen,
                        _relation_bind_address,
                        _mssql_db_client):
        _pwgen.return_value = 'db-user-password'
        _relation_bind_address.return_value = '192.168.1.1'

        self.harness.set_leader()
        self.harness.begin()
        self.harness.charm.mssql_peer = MssqlPeer(
            self.harness.charm, 'peers')
        self.harness.charm.mssql_provider = MssqlDBProvider(
            self.harness.charm, 'db')
        rel_id = self.harness.add_relation('db', 'wordpress')
        self.harness.add_relation_unit(rel_id, 'wordpress/0')
        self.harness.update_relation_data(
            rel_id,
            'wordpress/0',
            {
                'database': 'wordpress',
                'username': 'wordpress',
            })

        _mssql_db_client.assert_called_once_with('192.168.1.1')
        _pwgen.assert_called_once_with(32)
        _mssql_db_client.return_value.create_database.assert_called_once_with(
            'wordpress')
        _mssql_db_client.return_value.create_login.assert_called_once_with(
            'wordpress', 'db-user-password')
        _mssql_db_client.return_value.grant_access.assert_called_once_with(
            'wordpress', 'wordpress')


if __name__ == '__main__':
    unittest.main()
