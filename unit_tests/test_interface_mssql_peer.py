import unittest

from ops.testing import Harness
from ops.charm import CharmBase

from interface_mssql_peer import MssqlPeer


class TestInterfaceMssqlPeer(unittest.TestCase):

    def setUp(self):
        self.harness = Harness(CharmBase, meta='''
            name: mssql
            peers:
              peers:
                interface: mssql-peer
        ''')
        self.addCleanup(self.harness.cleanup)

    def add_peers_relation(self):
        self.peers = MssqlPeer(self.harness.charm, 'peers')
        peers_rel_id = self.harness.add_relation('peers', 'mssql')
        self.harness.add_relation_unit(peers_rel_id, 'mssql/1')
        return peers_rel_id

    def test_set_peers_rel_data_as_non_leader(self):
        self.harness.begin()
        self.harness.set_leader(False)
        self.add_peers_relation()
        self.peers.set_peers_rel_data({'key': 'value'})
        self.assertEqual(self.peers.get_peers_rel_data('key'), None)

    def test_set_peers_rel_data_leader(self):
        self.harness.begin()
        self.harness.set_leader(True)
        self.add_peers_relation()
        self.peers.set_peers_rel_data({'key': 'value'})
        self.assertEqual(self.peers.get_peers_rel_data('key'), 'value')


if __name__ == '__main__':
    unittest.main()
