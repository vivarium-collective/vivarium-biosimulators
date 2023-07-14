'''
    # node_id, biosimulator_config, connected_nodes # List of tuples. Each tuple contains (node_id, biosimulator_config, connected_nodes)
    (0, {'param1': 1.0, 'param2': 2.0}, [1, 2]),  # Node 0, connected to nodes 1 and 2
    (1, {'param1': 2.0, 'param2': 3.0}, [0, 2]),  # Node 1, connected to nodes 0 and 2
    (2, {'param1': 3.0, 'param2': 4.0}, [0, 1])   # Node 2, connected to nodes 0 and 1
'''

import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import Queue, Process
from typing import *
from enum import Enum
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulator_process import Biosimulator
from vivarium_biosimulators.experiments.test_biosimulators import ProcessController


class NodeController(Process):

    __PROCESS_CONTROLLER = ProcessController()

    def __init__(self,
                 node_id: int,
                 biosimulator_config: Dict,
                 input_queue,
                 output_queues,
                 process_controller: ProcessController = __PROCESS_CONTROLLER):
        super(NodeController, self).__init__()
        self.node_id = node_id
        self.biosimulator = Biosimulator(biosimulator_config)
        self.input_queue = input_queue
        self.output_queues = output_queues
        self.process_controller = process_controller

    def run(self):
        while True:
            # Check input_queue for new data
            while not self.input_queue.empty():
                new_data = self.input_queue.get()
                self.biosimulator.update_state(new_data)
            # Run a step of the Biosimulator
            # output = self.biosimulator.run_step()
            output = self.process_controller.run_biosimulator_process(**self.biosimulator.parameters)
            # Put the output in each output queue
            for output_queue in self.output_queues:
                output_queue.put((self.node_id, output))


class SingleNodeConfig:
    def __init__(self,
                 node_id: int = None,
                 biosimulator_config: Dict = None,
                 connected_nodes: List[int] = None):
        self.node_id = node_id
        self.biosimulator_config = biosimulator_config
        self.connected_nodes = connected_nodes
        self.values = (node_id, biosimulator_config, connected_nodes)


class Node:
    def __init__(self,
                 node_id=None,
                 biosimulator_config=None,
                 connected_nodes=None,
                 node_config: SingleNodeConfig = None):
        self.node_id = node_id
        self.biosimulator_config = biosimulator_config
        self.connected_nodes = connected_nodes  # List of Node objects this node is connected to
        self.node_config = node_config
        self.__parse_config()
        self.input_queue = Queue()
        self.controller = None

    def start(self, all_nodes):
        # Create a list of output queues for all connected nodes
        output_queues = [node.input_queue for node in all_nodes if node.node_id in self.connected_nodes]
        # Create and start the controller
        self.controller = NodeController(self.node_id, self.biosimulator_config, self.input_queue, output_queues)
        self.controller.start()

    def __parse_config(self):
        if self.node_config:
            self.node_id = self.node_config.config[0]
            self.biosimulator_config = self.node_config.config[1]
            self.connected_nodes = self.node_config.config[2]


class Orchestrator:
    @classmethod
    def orchestrate_nodes(cls,
                          node_configs: List[SingleNodeConfig],
                          *single_configs):
        """
        Parses node configurations and iterates over nodes.\n
        Args:\n
            :param:`node_configs(List[SingleNodeConfig])`: list of `SingleNodeConfig` objects to be run.
            :param:`*single_configs(SingleNodeConfig)`: single config objects to be parsed into a list.
        """
        all_nodes = []
        for config in node_configs:
            node = Node(config.node_id, config.biosimulator_config, config.connected_nodes)
            all_nodes.append(node)
        for node in all_nodes:
            node.start(all_nodes)
        # All nodes are now running

    @classmethod
    def plot_results(cls, nodes, results):
        for i in range(len(nodes)):
            plt.figure()
            plt.hist(results[:, i], bins=50, density=True)
            plt.xlabel(f'Simulation Outcome (Node {i})')
            plt.ylabel('Probability')
            plt.title(f'Monte Carlo Simulation Outcomes (Node {i})')
            plt.savefig(f'node_{i}_results.pdf')
        plt.show()

    @classmethod
    def create_perturbations(cls, n_runs: int, node_configs: List[SingleNodeConfig]):
        per = {}
        for r in range(n_runs):
            perturbations = np.random.normal(size=(len(node_configs), 2))
            per[r] = perturbations
        return per

    @classmethod
    def run_monte_carlo(cls, n_runs: int = 1000, n_steps: int = 50, node_configs: List[SingleNodeConfig] = None):
        '''
        Define the initial conditions of the Biosimulator parameters for each node and
        run a Monte Carlo simulation with the node graph.\n
            Args:
                :param:`n_runs[int]`: defines the number of monte carlo runs. Defaults to `1000`.
                :param:`n_steps[int]`: defines the number of steps for each simulation. Defaults to `50`.
        '''
        initial_configs = [
            {
                'param1': 0,
                'param2': 1,
            },
            {
                'param1': 2,
                'param2': 3,
            },
            {
                'param1': 4,
                'param2': 5,
            }
        ]
        # Prepare storage for simulation results
        results = []
        # Conduct the Monte Carlo simulation
        for run in range(n_runs):
            # Generate a random perturbation for each Biosimulator parameter for each node
            perturbations = np.random.normal(size=(len(initial_configs), 2))
            # Create nodes with perturbed Biosimulator configurations
            if not node_configs:
                node_configs = [
                    (
                        node_id,
                        {param: value + perturbation for param, value,
                            perturbation in zip(['param1', 'param2'], initial_config.values(), perturbation)},
                        [other_node_id for other_node_id in range(len(initial_configs)) if other_node_id != node_id],
                    )
                    for node_id, initial_config, perturbation in zip(range(len(initial_configs)), initial_configs, perturbations)
                ]

            nodes = []
            for node_id, biosimulator_config, connected_nodes in node_configs:
                node = Node(node_id, biosimulator_config, connected_nodes)
                nodes.append(node)

            for node in nodes:
                node.start(nodes)
            # Run the simulation for n_steps and record the results
            for step in range(n_steps):
                # Here, we're assuming that each NodeController's Biosimulator has a 'get_result' method
                result = [node.controller.biosimulator.get_result() for node in nodes]
                results.append(result)
            # Clean up processes after each run
            for node in nodes:
                node.controller.terminate()
        # Convert the list of results to a numpy array for easier manipulation
        results = np.array(results)
        cls.plot_results(nodes, results)
        return results


class SimulatorPaths(str, Enum):
    SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
    SBML_MODEL_PATH_ALT = 'vivarium_biosimulators/models/BIOMD0000000244_url.xml'
    BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'
    XPP_MODEL_PATH = 'Biosimulators_test_suite/examples/xpp/Wu-Biochem-Pharmacol-2006-pituitary-GH3-cells/GH3_Katp.ode'
    RBA_MODEL_PATH = 'Biosimulators_test_suite/examples/rba/Escherichia-coli-K12-WT/model.zip'
    BNGL_MODEL_PATH = 'Biosimulators_test_suite/examples/bngl/Dolan-PLoS-Comput-Biol-2015-NHEJ/Dolan2015.bngl'


class MonteCarloSetup(int, Enum):
    N_RUNS = 1000
    N_SIMULATION_STEPS = 50


class OrchestratedNodeBiosimulatorConfig(dict, Enum):
    node0_biosim_config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': SimulatorPaths.SBML_MODEL_PATH_ALT.value,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
        'total_time': 10.,
    }

    node1_biosim_config = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': SimulatorPaths.BIGG_MODEL_PATH.value,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    }

    node2_biosim_config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': SimulatorPaths.SBML_MODEL_PATH.value,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
        'default_output_value': np.array(3.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    }


ORCHESTRATED_SINGLE_NODE_GRAPH = {
    'NODE_0': SingleNodeConfig(
        node_id=0,
        biosimulator_config=OrchestratedNodeBiosimulatorConfig.node0_biosim_config.value,
        connected_nodes=[1, 2]
    ),
    'NODE_1': SingleNodeConfig(
        node_id=0,
        biosimulator_config=OrchestratedNodeBiosimulatorConfig.node1_biosim_config.value,
        connected_nodes=[0, 2]
    ),
    'NODE_2': SingleNodeConfig(
        node_id=2,
        biosimulator_config=OrchestratedNodeBiosimulatorConfig.node2_biosim_config.value,
        connected_nodes=[0, 1]
    ),
}


Orchestrator.orchestrate_nodes(node_configs=[node for node in ORCHESTRATED_SINGLE_NODE_GRAPH.values()])
