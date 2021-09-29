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
    defaults = {}
    def __init__(self, parameters=None):
        super().__init__(parameters)
    def ports_schema(self):
        return {}
    def next_update(self, timestep, states):
        return {}


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
        - ode_input_ports (dict):
        - ode_output_ports (dict):
        - fba_input_ports (dict):
        - fba_output_ports (dict):
        - ode_topology (dict):
        - fba_topology (dict):
        - default_store (str): The name of a default store, to use if a
            port mapping is not declared by ode_topology or fba_topology.
    """
    defaults = {
        'ode_config': None,
        'fba_config': None,
        'ode_input_ports': None,
        'ode_output_ports': None,
        'fba_input_ports': None,
        'fba_output_ports': None,
        'ode_topology': None,
        'fba_topology': None,
        'default_store': 'state',
    }
    def __init__(self, config=None):
        super().__init__(config)

        # ports for the processes
        self.ode_input_ports = self.config['ode_input_ports'] or {}
        self.ode_output_ports = self.config['ode_output_ports'] or {}
        self.fba_input_ports = self.config['fba_input_ports'] or {}
        self.fba_output_ports = self.config['fba_output_ports'] or {}

        # port: store mapping for ODE_FBA
        self.ode_topology = self.config['ode_topology'] or {}
        self.fba_topology = self.config['fba_topology'] or {}
        self.default_store = self.config['default_store']

    def generate_processes(self, config):

        # make the process configs
        ode_config = config['ode_config'] or {}
        fba_config = config['fba_config'] or {}

        ode_full_config = {
            'input_ports': self.ode_input_ports,
            'output_ports': self.ode_output_ports,
            **ode_config,
        }
        fba_full_config = {
            'input_ports': self.fba_input_ports,
            'output_ports': self.fba_output_ports,
            **fba_config,
        }

        # return initialized processes
        processes = {
            'ode': BiosimulatorProcess(ode_full_config),
            'fba': BiosimulatorProcess(fba_full_config),
        }
        return processes

    def generate_topology(self, config):

        # make the topologies
        ## ode topology
        ode_input_topology = {
            port: make_path(self.ode_topology.get(port, self.default_store))
            for port in self.ode_input_ports.keys()}
        ode_output_topology = {
            port: make_path(self.ode_topology.get(port, self.default_store))
            for port in self.ode_output_ports.keys()}
        if 'inputs' not in ode_input_topology:
            ode_input_topology['inputs'] = make_path(
                self.ode_topology.get('inputs', self.default_store))
        if 'outputs' not in ode_input_topology:
            ode_output_topology['outputs'] = make_path(
                self.ode_topology.get('outputs', self.default_store))

        ## fba topology
        fba_input_topology = {
            port: make_path(self.fba_topology.get(port, self.default_store))
            for port in self.fba_input_ports.keys()}
        fba_output_topology = {
            port: make_path(self.fba_topology.get(port, self.default_store))
            for port in self.fba_output_ports.keys()}
        if 'inputs' not in fba_input_topology:
            fba_input_topology['inputs'] = make_path(
                self.fba_topology.get('inputs', self.default_store))
        if 'outputs' not in fba_input_topology:
            fba_output_topology['outputs'] = make_path(
                self.fba_topology.get('outputs', self.default_store))

        # return the final topology
        topology = {
            'ode': {**ode_input_topology, **ode_output_topology},
            'fba': {**fba_input_topology, **fba_output_topology},
        }
        return topology
