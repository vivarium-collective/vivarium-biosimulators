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
from vivarium_biosimulators.library.mappings import remove_multi_update


class FluxBoundsConverter(Deriver):
    """Converts fluxes from ode simulator to flux bounds for fba simulator"""
    defaults = {
        'flux_to_bound_map': [],
        'ode_sync_step': None,  # TODO -- use the ODE simulator's timestep
    }
    def __init__(self, parameters=None):
        super().__init__(parameters)
        self.flux_to_bound_map = self.parameters['flux_to_bound_map']

    def ports_schema(self):
        if self.flux_to_bound_map:
            return {
                'fluxes': {
                    rxn_id: {'_default': 0.}
                    for rxn_id in self.flux_to_bound_map.keys()
                },
                'bounds': {
                    rxn_id: {'_default': 0., '_updater': 'set'}
                    for rxn_id in self.flux_to_bound_map.values()
                },
            }
        return {
            'fluxes': {},
            'bounds': {},
        }

    def next_update(self, timestep, states):

        # TODO -- use ode_sync_step to get flux

        if self.flux_to_bound_map:
            flux_bounds = {
                self.flux_to_bound_map[flux_id]: flux_value
                for flux_id, flux_value in states['fluxes'].items()
            }
            return {'bounds': flux_bounds}
        return {}



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
        - ode_input_to_output_map (dict): A map of input variable names to output variable names. For example,
            the variables' initial states might be inputs that are named differently from the outputs of the
            same variables (i.e. inputs with name 'init_conc_species_*' might need to map to 'dynamics_species_*').
        - default_store (str): The name of a default store, to use if a
            port mapping is not declared by ode_topology or fba_topology.
    """
    defaults = {
        'ode_config': None,
        'fba_config': None,
        'flux_to_bound_map': None,
        'ode_input_to_output_map': None,
        'default_store': 'state',
    }
    def __init__(self, config=None):
        super().__init__(config)
        self.flux_to_bound_map = self.config['flux_to_bound_map']
        self.flux_ids = [rxn_id for rxn_id in self.flux_to_bound_map.keys()]
        self.bounds_ids = [rxn_id for rxn_id in self.flux_to_bound_map.values()]
        self.ode_input_to_output_map = self.config['ode_input_to_output_map']
        self.default_store = self.config['default_store']

    def initial_state(self, config=None):
        initial_state = super().initial_state(config)
        return remove_multi_update(initial_state)

    def generate_processes(self, config):

        # make the ode config
        ode_full_config = {
            'output_ports': {'fluxes': self.flux_ids},
            'emit_ports': ['outputs', 'fluxes'],
            **config['ode_config'],
        }

        # make the fba config
        fba_full_config = {
            'input_ports': {'bounds': self.bounds_ids},
            'emit_ports': ['outputs', 'bounds'],
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

        # make a topology for ode inputs port. These might need to connect to
        # variables in the output port. And if they are in the flux_to_bound_map,
        # the inputs might  need to connect to 'fluxes'. For example,
        # {input: ('..', 'fluxes', output,)} instead of {input: (output,)}
        if self.ode_input_to_output_map:
            ode_input_to_output_topology = {}
            for input_name, output_name in self.ode_input_to_output_map.items():
                if output_name in self.flux_to_bound_map.keys():
                    ode_input_to_output_topology[input_name] = ('..', 'fluxes', output_name)
                else:
                    ode_input_to_output_topology[input_name] = (output_name,)
            ode_input_topology = {
                '_path': (self.default_store,),
                **ode_input_to_output_topology}
        else:
            ode_input_topology = (self.default_store,)

        # put together the composite topology
        topology = {
            'ode': {
                'fluxes': ('fluxes',),
                'inputs': ode_input_topology,
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
