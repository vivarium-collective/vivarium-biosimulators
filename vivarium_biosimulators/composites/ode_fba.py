"""
=================
ODE FBA Composite
=================

`ODE_FBA` is a :term:`Composer` that initializes and ODE BioSimulator, an FBA BioSimulator,
and wires them together so that the ODE model's flux outputs are used to constrain the FBA
model's flux bound inputs.
"""

from vivarium.core.process import Deriver
from vivarium.core.composer import Composer
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess


class FluxBoundsConverter(Deriver):
    """Converts fluxes from ode simulator to flux bounds for fba simulator"""
    defaults = {
        'flux_to_bound_map': []
    }
    def __init__(self, parameters=None):
        super().__init__(parameters)
        self.flux_to_bound_map = self.parameters['flux_to_bound_map']
    def ports_schema(self):
        return {
            'fluxes': {
                rxn_id: {
                    '_default': 0.,
                }
                for rxn_id in self.flux_to_bound_map.keys()
            },
            'bounds': {
                rxn_id: {
                    '_default': 0.,
                    '_updater': 'set',
                }
                for rxn_id in self.flux_to_bound_map.values()
            },
        }
    def next_update(self, timestep, states):
        # transform fluxes to flux_bounds
        flux_bounds = {
            self.flux_to_bound_map[flux_id]: flux_value
            for flux_id, flux_value in states['fluxes'].items()
        }
        return {
            'bounds': flux_bounds
        }


def make_path(key):
    if isinstance(key, str):
        return key,
    return key


class ODE_FBA(Composer):
    """ Makes an ODE/FBA Composite

    Config:
        - ode_config (dict): configuration for the ode biosimulator.
            Must include values for 'biosimulator_api', 'model_source',
            'simulation', and 'model_language'.
        - fba_config (dict): configuration for the fba biosimulator.
            Must include values for 'biosimulator_api', 'model_source',
            'simulation', and 'model_language'.
        - flux_to_bound_map (dict):
        - default_store (str): The name of a default store, to use if a
            port mapping is not declared by ode_topology or fba_topology.
    """
    defaults = {
        'ode_config': None,
        'fba_config': None,
        'flux_to_bound_map': None,
        'default_store': 'state',
    }
    def __init__(self, config=None):
        super().__init__(config)
        self.flux_to_bound_map = self.config['flux_to_bound_map']
        self.flux_ids = [rxn_id for rxn_id in self.flux_to_bound_map.keys()]
        self.bounds_ids = [rxn_id for rxn_id in self.flux_to_bound_map.values()]
        self.default_store = self.config['default_store']

    def generate_processes(self, config):

        # make the ode config
        ode_full_config = {
            'output_ports': {'fluxes': self.flux_ids},
            **config['ode_config'],
        }

        # make the fba config
        fba_full_config = {
            'input_ports': {'bounds': self.bounds_ids},
            **config['fba_config'],
        }

        # make the flux bounds config
        flux_bounds_config = {
            'flux_to_bound_map': self.flux_to_bound_map,
        }

        # return initialized processes
        processes = {
            'ode': BiosimulatorProcess(ode_full_config),
            'fba': BiosimulatorProcess(fba_full_config),
            'flux_bounds': FluxBoundsConverter(flux_bounds_config),
        }
        return processes

    def generate_topology(self, config):

        topology = {
            'ode': {
                'fluxes': ('fluxes',),
                'inputs': (self.default_store,),
                'outputs': (self.default_store,),
            },
            'fba': {
                'bounds': ('bounds',),
                'inputs': (self.default_store,),
                'outputs': (self.default_store,),
            },
            'flux_bounds': {
                'fluxes': ('fluxes',),
                'bounds': ('bounds',),
            },
        }
        return topology
