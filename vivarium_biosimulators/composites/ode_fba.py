"""
=================
ODE FBA Composite
=================
"""

from vivarium.core.composer import Composer
from vivarium_biosimulators.processes.biosimulators_process import BiosimulatorsProcess

SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'


class ODE_FBA(Composer):
    defaults = {
        'ode_config': {},
        'fba_config': {},
        'flux_map': {}  # {'ode_rxn_name': 'fba_bounds_name'}
    }

    def generate_processes(self, config):
        return {
            'ode_process': BiosimulatorsProcess(config['ode_config']),
            'fba_process': BiosimulatorsProcess(config['fba_config']),
        }

    def generate_topology(self, config):
        # TODO the flux output needs to be connected to fba's bounds input using flux_map
        return {
            'ode_process': {
                'input': ('state',),
                'output': ('state',),
            },
            'fba_process': {
                'input': ('state',),
                'output': ('state',),
            },
        }
