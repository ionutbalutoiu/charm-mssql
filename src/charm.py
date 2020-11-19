#!/usr/bin/env python3

import logging
import random
import string
import math
import re

from base64 import b64encode

from ops.charm import CharmBase
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus
from ops.main import main
from charmhelpers.core.hookenv import (
    leader_get,
    leader_set,
)

from interface_mssql import MssqlDBProvides

logger = logging.getLogger(__name__)


class MSSQLCharm(CharmBase):

    UNIT_ACTIVE_STATUS = ActiveStatus('Unit is ready')
    APPLICATION_ACTIVE_STATUS = ActiveStatus('MSSQL pod ready')
    MSSQL_PRODUCT_IDS = [
        'evaluation',
        'developer',
        'express',
        'web',
        'standard',
        'enterprise'
    ]

    def __init__(self, *args):
        super().__init__(*args)
        self.mssql_provider = MssqlDBProvides(self, 'db')

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_config_changed)
        self.framework.observe(self.on.leader_elected, self._on_config_changed)
        self.framework.observe(self.on.upgrade_charm, self._on_config_changed)

    def _on_config_changed(self, _):
        self._configure_pod()

    def _validate_product_id(self):
        product_id = self.model.config['product-id']
        if product_id.lower() in self.MSSQL_PRODUCT_IDS:
            return True

        logger.warning("The product id is not a standard MSSQL product id. "
                       "Checking if it's a product key.")
        if not self._is_product_key(product_id):
            logger.warning("Product id %s is not a valid product key",
                           product_id)
            return False

        return True

    def _validate_config(self):
        """Validates the charm config

        :returns: boolean representing whether the config is valid or not.
        """
        logger.info('Validating charm config')

        config = self.model.config
        required = ['image', 'product-id']
        missing = []
        for name in required:
            if not config.get(name):
                missing.append(name)
        if missing:
            msg = 'Missing configuration: {}'.format(missing)
            logger.warning(msg)
            self.unit.status = BlockedStatus(msg)
            return False

        if not self.model.config['accept-eula']:
            msg = 'The MSSQL EULA is not accepted'
            logger.warning(msg)
            self.unit.status = BlockedStatus(msg)
            return False

        if not self._validate_product_id():
            msg = 'Invalid MSSQL product id'
            logger.warning(msg)
            self.unit.status = BlockedStatus(msg)
            return False

        return True

    def _build_pod_spec(self):
        return {
            'version': 3,
            'containers': [{
                'name': self.app.name,
                'image': self.model.config['image'],
                'ports': [
                    {
                        'name': 'mssql',
                        'containerPort': 1433,
                        'protocol': 'TCP'
                    }
                ],
                'envConfig': {
                    'MSSQL_PID': self.model.config['product-id'],
                    'ACCEPT_EULA': self._accept_eula,
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

    def _build_pod_resources(self):
        sa_pass = b64encode(
            self._sa_password().encode('UTF-8')).decode('UTF-8')
        return {
            'kubernetesResources': {
                'secrets': [
                    {
                        'name': 'mssql',
                        'type': 'Opaque',
                        'data': {
                            'SA_PASSWORD': sa_pass,
                        }
                    }
                ]
            }
        }

    def _configure_pod(self):
        """Setup a new Microsoft SQL Server pod specification"""
        if not self.unit.is_leader():
            self.unit.status = self.UNIT_ACTIVE_STATUS
            return

        if not self._validate_config():
            logger.warning('Charm config is not valid')
            return

        logger.info("Setting pod spec")
        self.unit.status = MaintenanceStatus('Setting pod spec')

        pod_spec = self._build_pod_spec()
        pod_resources = self._build_pod_resources()
        self.model.pod.set_spec(pod_spec, pod_resources)

        self.app.status = self.APPLICATION_ACTIVE_STATUS
        self.unit.status = self.UNIT_ACTIVE_STATUS

    def _sa_password(self, length=32):
        sa_pass = leader_get('sa_password')
        if sa_pass:
            return sa_pass

        random_len = math.ceil(length/4)
        lower = ''.join(random.choice(string.ascii_lowercase)
                        for i in range(random_len))
        upper = ''.join(random.choice(string.ascii_uppercase)
                        for i in range(random_len))
        digits = ''.join(random.choice(string.digits)
                         for i in range(random_len))
        special = ''.join(random.choice(string.punctuation)
                          for i in range(random_len))

        sa_pass = lower + upper + digits + special
        leader_set(sa_password=sa_pass)

        return sa_pass

    def _is_product_key(self, key):
        regex = re.compile(r"^([A-Z]|[0-9]){5}(-([A-Z]|[0-9]){5}){4}$")
        if regex.match(key.upper()):
            return True
        return False

    @property
    def _accept_eula(self):
        if self.model.config['accept-eula']:
            return 'Y'
        return 'N'


if __name__ == "__main__":
    main(MSSQLCharm)
