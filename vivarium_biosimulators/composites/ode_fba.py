"""
=================
ODE FBA Composite
=================

`ODE_FBA` is a :term:`Composer` that initializes and ODE BioSimulator, an FBA BioSimulator,
and wires them together so that the ODE model's flux outputs are used to constrain the FBA
model's flux bound inputs.
"""

from vivarium.core.composer import Composer
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium_biosimulators.library.mappings import remove_multi_update
from vivarium_biosimulators.processes.flux_bounds import FluxBoundsConverter, get_flux_and_bound_ids


class ODE_FBA(Composer):
    """ Generates an ODE/FBA Composite

    Config:
        - ode_config (dict): configuration for the ode biosimulator.
            Must include values for 'biosimulator_api', 'model_source',
            'simulation', and 'model_language'.
        - fba_config (dict): configuration for the fba biosimulator.
            Must include values for 'biosimulator_api', 'model_source',
            'simulation', and 'model_language'.
        - flux_to_bounds_map (dict): a dictionary that maps the ODE process'
            reactions to flux bounds inputs to the FBA process.
        - default_store (str): The name of a default store, to use if a
            port mapping is not declared by ode_topology or fba_topology.
        - flux_unit (str): The unit of the ode process' flux output.
        - bounds_unit (str): The unit of the fba process' flux bounds input.
    """
    defaults = {
        'ode_config': None,
        'fba_config': None,
        'flux_to_bounds_map': None,
        'default_store_name': 'state',
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/L/s',
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.flux_to_bounds_map = self.config['flux_to_bounds_map']
        self.flux_ids, self.bounds_ids = get_flux_and_bound_ids(self.flux_to_bounds_map)
        self.default_store = self.config['default_store_name']

    def initial_state(self, config=None):
        initial_state = super().initial_state(config)
        return remove_multi_update(initial_state)

    def generate_processes(self, config):
        """
        generate the fba process, ode process, and ode flux to bounds converter process.
        """

        # make the fba process, and bounds port
        fba_full_config = {
            'input_ports': {'bounds': self.bounds_ids},
            'emit_ports': ['outputs', 'bounds'],
            **config['fba_config'],
        }
        fba_process = BiosimulatorProcess(fba_full_config)

        # make the ode process, and fluxes port
        ode_full_config = {
            'output_ports': {'fluxes': self.flux_ids},
            'emit_ports': ['outputs', 'fluxes'],
            **config['ode_config'],
        }
        ode_process = BiosimulatorProcess(ode_full_config)

        # make the ode flux bounds converter process,
        # which adds a bounds port on top of the ode_process
        flux_bounds_config = {
            'ode_process': ode_process,
            'flux_to_bounds_map': self.flux_to_bounds_map,
            'flux_unit': self.config['flux_unit'],
            'bounds_unit': self.config['bounds_unit'],
        }
        ode_flux_converter = FluxBoundsConverter(flux_bounds_config)

        # return initialized processes
        processes = {
            'ode': ode_flux_converter,
            'fba': fba_process,
        }
        return processes

    def generate_topology(self, config):
        """ put together the composite topology """
        topology = {
            'ode': {
                'fluxes': ('fluxes',),
                'bounds': ('bounds',),
                'inputs': (self.default_store,),
                'outputs': (self.default_store,),
            },
            'fba': {
                'bounds': ('bounds',),
                'inputs': (self.default_store,),
                'outputs': (self.default_store,),
            },
        }
        return topology
