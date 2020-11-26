"""
Implementation of the MSSQL charm peer relation.
"""

import logging

from ops.framework import Object

logger = logging.getLogger(__name__)


class MssqlPeer(Object):

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        self.app = self.model.app
        self.unit = self.model.unit

    def set_peers_rel_data(self, data={}, **kwargs):
        if not self.unit.is_leader():
            logger.warning('Unit is not leader. '
                           'Skipping set_peers_rel_data().')
            return
        data.update(kwargs)
        rel = self.peers_rel
        for key, value in data.items():
            rel.data[self.app][key] = value

    def get_peers_rel_data(self, var_name):
        rel = self.peers_rel
        return rel.data[self.app].get(var_name)

    @property
    def peers_rel(self):
        return self.framework.model.get_relation(self.relation_name)

    @property
    def peers_binding(self):
        return self.framework.model.get_binding(self.peers_rel)

    @property
    def peers_bind_address(self):
        return str(self.peers_binding.network.bind_address)
