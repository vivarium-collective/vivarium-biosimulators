"""
====================
BioSimulator Process
====================

`BiosimulatorProcess` is a general Vivarium :term:`process class` that can load any
BioSimulator and model, and run it.

KISAO: https://bioportal.bioontology.org/ontologies/KISAO
"""

import importlib
import copy

from vivarium.core.process import Process

from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, 
    UniformTimeCourseSimulation, SteadyStateSimulation
)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_outputs_for_simulation


TIME_COURSE_SIMULATIONS = ['uniform_time_course', 'analysis']


def get_delta(before, after):
    # TODO -- make this work for BioNetGen, MCell.
    # TODO -- different method for different data types
    return after - before


class BiosimulatorProcess(Process):
    """ A Vivarium wrapper for any BioSimulator

    Config:
        - biosimulator_api (str): the name of the imported biosimulator api
        - model_source (str): a path to the model file
        - model_language (str): the model language, select from biosimulators_utils.sedml.data_model.ModelLanguage
        - simulation (str): select from 'uniform_time_course', 'steady_state', 'one_step', 'analysis'
        - input_ports (dict): a dictionary mapping {'input_port_name': ['list', 'of', 'variables']}
        - output_ports (dict): a dictionary mapping {'output_port_name': ['list', 'of', 'variables']}
        - default_input_port_name (str): the default input port name for variables not specified by input_ports
        - default_output_port_name (str): the default output port name for variables not specified by output_ports
        - emit_ports (list): a list of the ports whose values are emitted
        - time_step (float): the synchronization time step

    # TODO -- configurable default types for individual variables
    # TODO -- pass in Algorithm object, and parameters
    """
    
    defaults = {
        'biosimulator_api': '',
        'model_source': '',
        'model_language': '',
        'simulation': 'uniform_time_course',
        'input_ports': None,
        'output_ports': None,
        'default_input_port_name': 'inputs',
        'default_output_port_name': 'outputs',
        'default_input_value': 0.,  # TODO -- scalar (int, float, bool), depends on model language
        'default_output_value': 0.,  # TODO -- if steady_state then np scalar
        'emit_ports': ['outputs'],
        'kisao_id': None,
        'time_step': 1.,
        'port_schema': {},  # TODO -- pass information about data type, updater. like _schema
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        # import biosimulator module
        biosimulator = importlib.import_module(self.parameters['biosimulator_api'])
        self.exec_sed_task = getattr(biosimulator, 'exec_sed_task')
        self.preprocess_sed_task = getattr(biosimulator, 'preprocess_sed_task')

        # get the model
        model = Model(
            id='model',
            source=self.parameters['model_source'],
            language=self.parameters['model_language'],
        )

        # get the simulation
        simulation = None
        if self.parameters['simulation'] in TIME_COURSE_SIMULATIONS:
            simulation = UniformTimeCourseSimulation(
                id='simulation',
                initial_time=0.,
                output_start_time=0.,
                number_of_points=1,
                output_end_time=self.parameters['time_step'],
                algorithm=Algorithm(
                    kisao_id=self.parameters['kisao_id'] or 'KISAO_0000019'),
            )
        elif self.parameters['simulation'] == 'steady_state':
            simulation = SteadyStateSimulation(
                id='simulation',
                algorithm=Algorithm(
                    kisao_id=self.parameters['kisao_id'] or 'KISAO_0000437'),
            )

        # make the task
        self.task = Task(
            id='task',
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        self.inputs, _, self.outputs, _ = get_parameters_variables_outputs_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__,
            algorithm_kisao_id=simulation.algorithm.kisao_id,
        )

        # make an map of input ids to targets
        self.input_id_target_map = {}
        for variable in self.inputs:
            self.input_id_target_map[variable.id] = variable.target

        # assign outputs to task
        for variable in self.outputs:
            variable.task = self.task

        self.config = Config(LOG=False)

        # pre-process
        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.outputs,
            config=self.config,
        )

        # port assignments
        self.port_assignments = {}
        self.input_ports = []
        self.output_ports = []
        all_inputs = [input_state.id for input_state in self.inputs]
        all_outputs = [output_state.id for output_state in self.outputs]
        remaining_inputs = copy.deepcopy(all_inputs)
        remaining_outputs = copy.deepcopy(all_outputs)

        if self.parameters['input_ports']:
            for port_id, variables in self.parameters['input_ports'].items():
                if isinstance(variables, str):
                    variables = [variables]
                for variable_id in variables:
                    assert variable_id in all_inputs, \
                        f"port assigments: variable id '{variable_id}' is not in the available inputs:{all_inputs} "
                    remaining_inputs.remove(variable_id)
                self.port_assignments[port_id] = variables
                self.input_ports.append(port_id)

        if remaining_inputs:
            default_input_port_id = self.parameters['default_input_port_name']
            self.port_assignments[default_input_port_id] = remaining_inputs
            self.input_ports.append(default_input_port_id)

        if self.parameters['output_ports']:
            for port_id, variables in self.parameters['output_ports'].items():
                if isinstance(variables, str):
                    variables = [variables]
                for variable_id in variables:
                    assert variable_id in all_outputs, \
                        f"port assigments: variable id '{variable_id}' is not in the available outputs: {all_outputs} "
                    remaining_outputs.remove(variable_id)
                self.port_assignments[port_id] = variables
                self.output_ports.append(port_id)

        if remaining_outputs:
            default_output_port_id = self.parameters['default_output_port_name']
            self.port_assignments[default_output_port_id] = remaining_outputs
            self.output_ports.append(default_output_port_id)

    def initial_state(self, config=None):
        """
        extract initial state according to port_assignments
        """
        initial_state = {
            'global_time': 0
        }
        input_values = {
            input_state.id: float(input_state.new_value)  # TODO (ERAN) -- tellurium gets a str here, float() might not always apply
            for input_state in self.inputs}

        # run task to view initial values
        results = self.run_task(
            input_values, 0, self.parameters['time_step'])
        output_values = self.process_results(
            results, time_course_index=0)

        for port_id, variables in self.port_assignments.items():
            if port_id in self.input_ports:
                initial_state[port_id] = {
                    variable: input_values[variable]
                    for variable in variables
                }
            elif port_id in self.output_ports:
                initial_state[port_id] = {
                    variable: output_values[variable]
                    for variable in variables
                }
        return initial_state

    def is_deriver(self):
        if self.parameters['simulation'] in TIME_COURSE_SIMULATIONS:
            return False
        return True

    def ports_schema(self):
        """ make port schema for all ports and variables in self.port_assignments """
        schema = {
            'global_time': {'_default': 0.}
        }
        for port_id, variables in self.port_assignments.items():
            emit_port = port_id in self.parameters['emit_ports']
            schema[port_id] = {
                variable: {
                    '_default': self.parameters['default_output_value'] if
                    port_id in self.output_ports else self.parameters['default_input_value'],
                    '_updater': 'accumulate',
                    '_emit': emit_port,
                } for variable in variables
            }
        return schema

    def run_task(self, inputs, initial_time, interval):

        # update model based on input
        self.task.changes = []
        for variable_id, variable_value in inputs.items():
            self.task.changes.append(ModelAttributeChange(
                target=self.input_id_target_map[variable_id],
                new_value=variable_value,
            ))

        # set the simulation time
        self.task.simulation.initial_time = initial_time
        self.task.simulation.output_start_time = initial_time
        self.task.simulation.output_end_time = initial_time + interval

        # execute step
        raw_results, log = self.exec_sed_task(
            self.task,
            self.outputs,
            preprocessed_task=self.preprocessed_task,
            config=self.config,
        )
        return raw_results

    def process_result(self, result, time_course_index=-1):
        if self.parameters['simulation'] in TIME_COURSE_SIMULATIONS:
            value = result[time_course_index]
        else:
            value = result
        return value

    def process_results(self, results, time_course_index=-1):
        values = {}
        for result_id, result in results.items():
            values[result_id] = self.process_result(result, time_course_index)
        return values

    def next_update(self, interval, states):

        # collect the inputs
        input_values = {}
        for port_id in self.input_ports:
            input_values.update(states[port_id])

        # set the simulation time
        global_time = states['global_time']

        # run task
        raw_results = self.run_task(input_values, global_time, interval)

        # transform results
        update = {}
        for port_id in self.output_ports:
            variable_ids = self.port_assignments[port_id]
            if variable_ids:
                update[port_id] = {}
                for variable_id in variable_ids:
                    raw_result = raw_results[variable_id]
                    value = self.process_result(raw_result)

                    # TODO -- different get_delta for different data types?
                    update[port_id][variable_id] = get_delta(
                        states[port_id][variable_id], value)
        return update
