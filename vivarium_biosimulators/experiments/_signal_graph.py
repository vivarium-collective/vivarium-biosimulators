'''
Graph:
    :param:`n_nodes(int)`: Number of nodes in the graph
    :param:`input_signal(Any)`: Input data for the head node that will be 
        processed down the graph.
    :param:`node_config(List[SingleNodeConfig])`: A list of configured
        `SingleNodeConfig` objects
        

SingleNodeConfig:
    :param:`id(str)`: index spot
    :param:
'''

from enum import Enum
from typing import Dict, List, Union, Optional, Tuple
import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.experiments.biosimulator_configs import GET_ALL_MODEL_FILES, BIOSIMULATOR_SPECS, SBML_MODEL_PATH, BIGG_MODEL_PATH
from vivarium_biosimulators.experiments.multiprocess_graph import SingleNodeConfig
from vivarium_biosimulators.processes.biosimulator_process import Biosimulator


'''
Node:

- ID:
    =>  self.id: str = id of node (perhaps 0, 1, 2...but it can be custom)

- Steaming data (Biosimulator(Process)):
    =>  self.parameters:
            => SMI (substantial model info): 'input_port(dict)', 'output_port(dict)', 'biosimulator_api', 'initial_state', etc
        results:
            => Simulator task ouput results (simulator results)

- Controller:
    =>  self.input = Biosimulator.parameters['input_port']
        self.output = Biosimulator.parameters['output_port']
        
                

'''


class PortInterface:
    def __init__(self, node_id: str, name: str, process: Biosimulator, value: Dict):
        raise NotImplementedError

    def get_data(self, process: Biosimulator):
        raise NotImplementedError

    def set_data(self):
        raise NotImplementedError


class Port(PortInterface):
    def __init__(self, node_id: str, name: str, process: Biosimulator, process_ports_key: str):
        """
        Params:
            :param:`node_id`(`str`): id for the node that this port belongs to which links together node members.
            :param:`name`(`str`):: id for the port
            :param:`process`(`Biosimulator`): linked process that the value is derived from.
            :param:`process_ports_key`(`str`): name of the ports key derived from the relative
                `process`.
        """
        self.node_id = node_id
        self.name = name
        self.value = self.get_data(process, process_ports_key)

    def get_data(self, process: Biosimulator, ports_key: str):
        return process.parameters[ports_key]

    def set_data(self, process: Biosimulator, ports_key: str, value):
        process.parameters[ports_key] = value
        return process


class InputPort(Port):
    def __init__(self, node_id: str, process: Biosimulator, name: str = 'input'):
        self.process_ports_key = 'input_ports'
        super().__init__(node_id, name, process, self.process_ports_key)


class OutputPort(Port):
    def __init__(self, node_id: str, process: Biosimulator, name: str = 'output'):
        self.process_ports_key = 'output_ports'
        super().__init__(node_id, name, process, self.process_ports_key)


class ControllerInterface:
    def __init__(self, node_id: str, input_port: InputPort, output_port: OutputPort, process: Biosimulator):
        raise NotImplementedError

    def adjust_process_parameter(self, field: str = None, value=None):
        '''change a given field (`field`) in self.process.parameters'''
        raise NotImplementedError

    def verify_inbound_parameters(self) -> bool:
        '''
        Check incoming process parameters against current parameters (which originate from previous_node.process.parameters).\n
        Logic:\n
            `return self.input_port.value (AKA: previous_node.process.parameters) == self.process.parameters`
        '''
        raise NotImplementedError

    def get_data_from_process(self):
        '''for streaming output...process comes from self.process'''
        raise NotImplementedError

    def get_data_from_input(self):
        '''recieve data from previous node aka self.input_port.value...for changing input value of `Biosimulator`'''
        raise NotImplementedError

    def stream_process_data_for_output(self):
        '''
        Push Simulator result data to output_port value.\n
        Logic:\n
            `process == self.process & output_port == self.output_port`\n
            `data = self.get_data_from_process(self.process['output_ports'])`\n
            `self.output_port.value = data`
        '''
        raise NotImplementedError

    def set_input_value(self):
        '''
        Get value from `input_port` and set it as the input value of `process`\n.
        Logic:\n
            `process == self.process & input_port == self.input_port`\n
            `data = self.get_data_from_input(self.input_port)`\n
            `self.process.parameters = data
        '''
        raise NotImplementedError


class Controller(ControllerInterface):
    def __init__(self, node_id: str, input_port: InputPort, output_port: OutputPort, process: Biosimulator):
        self.node_id = node_id
        self.input_port = input_port
        self.output_port = output_port
        self.process = process
        # self.read_input()

    def get_port_data(self, port: str):
        return self.process.parameters[port]

    def get_input_port_data(self):
        return self.get_port_data('input_ports')

    def get_output_port_data(self):
        return self.get_port_data('output_ports')

    def adjust_process_parameter(self, field: str, value):
        self.process.parameters[field] = value

    def verify_inbound_parameters(self, incoming_parameters: Dict = None) -> bool:
        return incoming_parameters == self.process.parameters

    def get_data_from_input(self):
        return self.input_port.value

    def set_input_value(self):
        incoming_data = self.get_data_from_input()
        if not self.verify_inbound_parameters(incoming_data):
            self.process.parameters = incoming_data

    def get_data_from_process(self):
        return self.get_port_data('output_ports')

    def stream_process_data_for_output(self):
        outbound_data = self.get_data_from_process()
        self.output_port.value = outbound_data


class NodeInterface:
    def __init__(self,
                 node_id: str,
                 process: Biosimulator,
                 input_port: InputPort,
                 output_port: OutputPort,
                 controller: Controller,
                 connected_nodes: List[str],
                 biosimulator_config: Optional[Dict],
                 next_node=None,
                 graph_connection=None):
        raise NotImplementedError

    def scan_next_node(self):
        '''Read value for next node.'''
        raise NotImplementedError


class Graph:
    def __init__(self, n_iterations: int = 1, nodes: Union[List, Dict] = None):
        self.nodes = nodes
        self.n_iterations = n_iterations

    def add_node(self, id, val):
        self.nodes[id] = val

    def get_vals(self):
        return {'nodes': self.nodes, 'num_iterations': self.n_iterations}

    def execute(self):
        if self.n_iterations >= 1:
            for n in range(self.n_iterations):
                print(f'Iteration number: {n}')
                for node in self.nodes:
                    print(node)
        else:
            print('Iterations: None')
            print(dir(self))

    def _execute(self):
        if self.n_iterations >= 1:
            for n in range(self.n_iterations):
                print(n, self.nodes.keys(), self.nodes.values())
        else:
            v = self.get_vals()
            print(v)


class NodeConnection:
    def __init__(self, _input: Union[int, str, None] = None, _output: Union[int, str, None] = None):
        '''
        Helper class for mapping nodes within a graph.\n
        Params:\n
            :param:`_input(Union[int, None])`:id of Node that the given node recieves input from. Defaults to`None`.\n
            :param:`_output(Union[int, None])`:id of Node that the given node emits output to. Defaults to`None`.\n
        Returns:\n
            :param:`value`(`Tuple[Union[int, str, None], Union[int, str, None]]`): a tuple of `(_input, _output)`.

        '''
        self.value = (_input, _output)


class Node(NodeInterface):
    def __init__(self,
                 node_id: str,
                 connected_nodes: NodeConnection = None,
                 biosimulator_config: Optional[Dict] = None,
                 graph_connection: Graph = None):
        '''
        Abstract Class for creating Node Instances.\n
        Params:\n
            :param:`node_id`(`str`): id of this node that will be fed to the other attribute objects.\n
            :param:`connected_nodes`(`List[str]`): list of `Node().id` 's relative to this node that it is connected to.\n
            :param:`biosimulator_config`(`Dict`): configuration for the Biosimulator instance.
            :param:`next_node`(`Node`): adjacent (on the right) node in the Node graph. Defaults to `None`.
        '''
        self.node_id = node_id
        self.connected_nodes = connected_nodes.value
        self.graph_connection = graph_connection
        self.process = Biosimulator(parameters=biosimulator_config)
        self.input_port = InputPort(node_id=self.node_id, process=self.process)
        self.output_port = OutputPort(self.node_id, self.process)
        self.controller = Controller(node_id=self.node_id,
                                     input_port=self.input_port,
                                     output_port=self.output_port,
                                     process=self.process)
        self.next_node = self._scan_next_node()

    def run(self):
        print((self.node_id, self.connected_nodes, self.graph_connection, self.process,
              self.input_port, self.output_port, self.controller, self.next_node))

    def _scan_next_node(self):
        return self.connected_nodes[1]

    def represent(self):
        return {
            'id': self.node_id,
            'connected': self.connected_nodes,
            'connected_graph_nodes': self.graph_connection.nodes,
            'process_params': self.process.parameters,
            'input_port': {
                'node_id': self.input_port.node_id,
                'name': self.input_port.name,
            },
            'output_port': {
                'node_id': self.output_port.node_id,
                'name': self.output_port.name,
            },
            'controller': {
                'value': self.controller.input_port.value,
                'output': self.controller.output_port.value,
            },
            'next_node': self.next_node,
        }


class BiosimulatorConfig(dict, Enum):
    HEAD = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        },
    }

    NODE_1 = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        },
    }

    NODE_2 = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        },
    }

    TAIL = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        },
    }


def create_head_node(
    graph_connection: Graph
) -> Node:
    node_id = 'head'
    connection = NodeConnection(None, 1)
    config = BiosimulatorConfig.HEAD
    return Node(node_id,
                connection,
                config,
                graph_connection)


def create_tail_node(
    prev_node_conn: int,
    graph_connection: Graph
) -> Node:
    node_id = 'tail'
    connection = NodeConnection(prev_node_conn, None)
    config = BiosimulatorConfig.TAIL
    return Node(node_id,
                connection,
                config,
                graph_connection)


def create_inner_node(
    node_id: str,
    connection: NodeConnection,
    config: BiosimulatorConfig,
    graph_connection: Graph
) -> Node:
    return Node(node_id,
                connection,
                config,
                graph_connection)


if __name__ == '__main__':
    # define number of iterations
    num_iterations = 1

    # define the object to store the graph nodes, etc
    graph = Graph(n_iterations=num_iterations, nodes={})

    print(f'Here are the graph nodes: {graph.nodes}')

    # create head node
    node_0 = create_head_node(graph)
    # add head node to graph
    graph.add_node('0', node_0)

    # create inner node connection
    connection_node_1 = NodeConnection(0, 1)
    # create tag for inner node
    name_node_1 = 'cobrapy_1'
    # create inner node 1:
    node_1 = create_inner_node(
        name_node_1,
        connection_node_1,
        BiosimulatorConfig.NODE_1,
        graph
    )
    # add inner node 1 to graph:
    graph.add_node('1', node_1)

    # repeat the process for another inner node
    connection_node_2 = NodeConnection(1, 2)
    name_node_2 = 'cobrapy_2'
    node_2 = create_inner_node(
        name_node_2,
        connection_node_2,
        BiosimulatorConfig.NODE_2,
        graph
    )
    graph.add_node('2', node_2)

    # create tail node,repeating the same process
    node_3 = create_tail_node(
        prev_node_conn=2,
        graph_connection=graph
    )
    graph.add_node('3', node_3)

    print(f'Here are the graph nodes now:\n{graph.nodes}\n')

    for node in graph.nodes.keys():
        print(f'Name: {node}')
        print(graph.nodes[node].represent())
