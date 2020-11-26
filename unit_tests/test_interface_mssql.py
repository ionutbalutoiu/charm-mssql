import unittest

from ops.testing import Harness
from ops.charm import CharmBase

from unittest import mock

from interface_mssql import MssqlDBProvides


class TestInterfaceMssql(unittest.TestCase):

    def setUp(self):
        self.harness = Harness(CharmBase, meta='''
            name: mssql
            provides:
              db:
                interface: mssql
        ''')
        self.addCleanup(self.harness.cleanup)

    @mock.patch.object(MssqlDBProvides, 'mssql_db_client')
    @mock.patch.object(MssqlDBProvides, 'relation_bind_address')
    @mock.patch('charmhelpers.core.host.pwgen')
    def test_on_changed(self,
                        _pwgen,
                        _relation_bind_address,
                        _mssql_db_client):
        _pwgen.return_value = 'db-user-password'
        _relation_bind_address.return_value = '192.168.1.1'

        self.harness.begin()
        self.harness.set_leader()
        self.mssql_provider = MssqlDBProvides(self.harness.charm, 'db')
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
