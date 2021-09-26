"""
=================
ODE FBA Composite
=================
"""

from vivarium.core.process import Deriver
from vivarium.core.composer import Composer
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess


class FluxBoundsConverter(Deriver):
    """Converts fluxes from ode simulator to flux bounds for fba simulator"""
    defaults = {}
    def __init__(self, parameters=None):
        super().__init__(parameters)
    def ports_schema(self):
        return {}
    def next_update(self, timestep, states):
        return {}


class ODE_FBA(Composer):
    """Makes ODE/FBA Composite

    Config options:
        - ode_config (dict):
        - fba_config (dict):
        - flux_map (dict):
    """
    defaults = {
        'ode_config': {},
        'fba_config': {},
        'flux_map': {}  # {'ode_rxn_name': 'fba_bounds_name'}
    }
    def __init__(self, config=None):
        super().__init__(config)

    def generate_processes(self, config):
        return {
            'ode_process': BiosimulatorProcess(config['ode_config']),
            'fba_process': BiosimulatorProcess(config['fba_config']),
        }

    def generate_topology(self, config):
        # TODO the flux output needs to be connected to fba's bounds input using flux_map
        return {
            'ode_process': {
                'inputs': ('state',),
                'outputs': ('state',),
            },
            'fba_process': {
                'inputs': ('state',),
                'outputs': ('state',),
            },
        }
