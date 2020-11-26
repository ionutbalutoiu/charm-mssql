import unittest

from base64 import b64encode

from ops.model import BlockedStatus
from ops.testing import Harness

from mock import patch

import charm


class TestMssqlCharm(unittest.TestCase):

    def setUp(self):
        self.harness = Harness(charm.MSSQLCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader()

    def add_peers_relation(self):
        rel_id = self.harness.add_relation('peers', 'mssql')
        self.harness.add_relation_unit(rel_id, 'mssql/1')
        return rel_id

    def test_non_leader_unit(self):
        self.harness.begin()
        self.harness.set_leader(False)
        self.harness.update_config({
            'product-id': 'Invalid product id',
            'accept-eula': False
        })
        self.assertEqual(self.harness.charm.unit.status,
                         self.harness.charm.UNIT_ACTIVE_STATUS)

    def test_config_invalid_product_id(self):
        self.harness.begin()
        self.harness.update_config({
            'product-id': 'Invalid product id',
            'accept-eula': True
        })
        expected = BlockedStatus('Invalid MSSQL product id')
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_config_valid_product_id(self):
        self.harness.begin()
        self.harness.disable_hooks()
        self.harness.update_config({
            'product-id': 'Enterprise',
            'accept-eula': True
        })
        self.assertEqual(self.harness.charm._validate_config(), True)

    def test_config_valid_product_key(self):
        self.harness.begin()
        self.harness.disable_hooks()
        self.harness.update_config({
            'product-id': 'ABC00-ABC11-ABC22-ABC33-ABC44',
            'accept-eula': True
        })
        self.assertEqual(self.harness.charm._validate_config(), True)

    def test_config_missing_mandatory_value(self):
        self.harness.begin()
        self.harness.update_config({'product-id': None})
        expected = BlockedStatus(
            'Missing configuration: {}'.format(['product-id']))
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_config_missing_eula_accept(self):
        self.harness.begin_with_initial_hooks()
        expected = BlockedStatus('The MSSQL EULA is not accepted')
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_build_pod_spec(self):
        self.harness.begin()
        self.harness.disable_hooks()
        self.harness.update_config({
            'product-id': 'Developer',
            'accept-eula': True
        })
        expected = {
            'version': 3,
            'containers': [{
                'name': 'mssql',
                'image': 'mcr.microsoft.com/mssql/server:2019-latest',
                'ports': [
                    {
                        'name': 'mssql',
                        'containerPort': 1433,
                        'protocol': 'TCP'
                    }
                ],
                'envConfig': {
                    'MSSQL_PID': 'Developer',
                    'ACCEPT_EULA': 'Y',
                    'mssql-secret': {
                        'secret': {
                            'name': 'mssql'
                        }
                    }
                },
                'kubernetes': {
                    'readinessProbe': {
                        'tcpSocket': {
                            'port': 1433
                        },
                        'initialDelaySeconds': 3,
                        'periodSeconds': 3
                    }
                }
            }]
        }
        self.assertEqual(self.harness.charm._build_pod_spec(), expected)

    def test_build_pod_resources(self):
        rel_id = self.add_peers_relation()
        self.harness.update_relation_data(
            rel_id,
            'mssql',
            {'sa_password': 'strong-password'})
        self.harness.begin()
        self.harness.disable_hooks()
        expected_sa_pass = b64encode(
            'strong-password'.encode('UTF-8')).decode('UTF-8')
        expected = {
            'kubernetesResources': {
                'secrets': [
                    {
                        'name': 'mssql',
                        'type': 'Opaque',
                        'data': {
                            'SA_PASSWORD': expected_sa_pass,
                        }
                    }
                ]
            }
        }
        self.assertEqual(self.harness.charm._build_pod_resources(), expected)

    def test_app_start_existing_sa_pass(self):
        rel_id = self.add_peers_relation()
        self.harness.update_relation_data(
            rel_id,
            'mssql',
            {'sa_password': 'strong-password'})
        self.harness.begin()
        self.harness.update_config({
            'product-id': 'Enterprise',
            'accept-eula': True
        })
        self.assertEqual(self.harness.charm.unit.status,
                         self.harness.charm.UNIT_ACTIVE_STATUS)
        self.assertEqual(self.harness.charm.app.status,
                         self.harness.charm.APPLICATION_ACTIVE_STATUS)

    @patch.object(charm.secrets, 'choice')
    def test_app_start_new_sa_pass(self, _choice):
        self.add_peers_relation()
        _choice.return_value = 'r'
        self.harness.begin()
        self.harness.update_config({
            'product-id': 'Enterprise',
            'accept-eula': True
        })
        expected_sa_pass = 'r' * 32
        self.assertEqual(
            self.harness.charm.mssql_peer.get_peers_rel_data('sa_password'),
            expected_sa_pass)
        self.assertEqual(self.harness.charm.unit.status,
                         self.harness.charm.UNIT_ACTIVE_STATUS)
        self.assertEqual(self.harness.charm.app.status,
                         self.harness.charm.APPLICATION_ACTIVE_STATUS)
