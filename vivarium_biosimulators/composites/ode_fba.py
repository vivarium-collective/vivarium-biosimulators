"""
=================
ODE FBA Composite
=================

`ODE_FBA` is a :term:`Composer` that initializes and ODE BioSimulator, an FBA BioSimulator,
and wires them together so that the ODE model's flux outputs are used to constrain the FBA
model's flux bound inputs.
"""

from vivarium.core.process import Process
from vivarium.core.composer import Composer
from vivarium.library.units import units
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium_biosimulators.library.mappings import remove_multi_update


class FluxBoundsConverter(Process):
    """A wrapper for an ode process

    Converts the ode's output fluxes to flux bounds inputs for an fba process.

    TODO (ERAN) -- adjust both upper and lower bounds?
    """
    defaults = {
        'flux_to_bound_map': {},
        'ode_process': None,
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/L/s',
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)
        self.flux_to_bound_map = self.parameters['flux_to_bound_map']
        self.ode_process = self.parameters['ode_process']
        self.inputs = self.ode_process.inputs
        self.outputs = self.ode_process.outputs
        self.input_ports = self.ode_process.input_ports
        self.output_ports = self.ode_process.output_ports

        # unit conversion
        self.flux_unit = units(self.parameters['flux_unit'])
        self.bounds_unit = units(self.parameters['bounds_unit'])

    def initial_state(self, config=None):
        state = self.ode_process.initial_state(config)
        state['bounds'] = {}
        return state

    def calculate_timestep(self, states):
        return self.ode_process.calculate_timestep(states)

    def ports_schema(self):
        """
        Use the ode process's ports, with an added 'bounds' port to output the flux bounds.
        """
        ports = self.ode_process.get_schema()
        ports['bounds'] = {}
        for rxn_id in ports['fluxes'].keys():
            bound_id = self.flux_to_bound_map[rxn_id]
            ports['bounds'][bound_id] = {'_updater': 'set'}
        return ports

    def convert_fluxes(self, fluxes, dt):
        """
        divide by the time step to get flux bounds, and convert to bounds unit
        """
        flux_bounds = {
            self.flux_to_bound_map[flux_id]: (
                flux_value / dt * (self.flux_unit / units.s)
            ).to(self.bounds_unit).magnitude
            for flux_id, flux_value in fluxes.items()
        }
        return flux_bounds

    def next_update(self, interval, states):
        update = self.ode_process.next_update(interval, states)
        update['bounds'] = self.convert_fluxes(update['fluxes'], interval)
        return update


class ODE_FBA(Composer):
    """ Generates an ODE/FBA Composite

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
        - flux_unit (str): The unit of the ode process' flux output
        - bounds_unit (str): The unit of the fba process' flux bounds input
    """
    defaults = {
        'ode_config': None,
        'fba_config': None,
        'flux_to_bound_map': None,
        'ode_input_to_output_map': None,
        'default_store': 'state',
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/L/s',
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

        # make the ode process
        ode_full_config = {
            'output_ports': {'fluxes': self.flux_ids},
            'emit_ports': ['outputs', 'fluxes'],
            **config['ode_config'],
        }
        ode_process = BiosimulatorProcess(ode_full_config)

        # make the fba process
        fba_full_config = {
            'input_ports': {'bounds': self.bounds_ids},
            'emit_ports': ['outputs', 'bounds'],
            **config['fba_config'],
        }
        fba_process = BiosimulatorProcess(fba_full_config)

        # make the ode flux bounds converter process
        flux_bounds_config = {
            'ode_process': ode_process,
            'flux_to_bound_map': self.flux_to_bound_map,
            'flux_unit': self.parameters['flux_unit'],
            'bounds_unit': self.parameters['bounds_unit'],
        }
        ode_flux_converter = FluxBoundsConverter(flux_bounds_config)

        # return initialized processes
        processes = {
            'ode': ode_flux_converter,
            'fba': fba_process,
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
                'bounds': ('bounds',),
                'inputs': ode_input_topology,
                'outputs': (self.default_store,),
            },
            'fba': {
                'bounds': ('bounds',),
                'inputs': (self.default_store,),
                'outputs': (self.default_store,),
            },
        }
        return topology
