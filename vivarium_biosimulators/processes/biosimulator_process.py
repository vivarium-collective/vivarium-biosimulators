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
        'algorithm': {
            'kisao_id': 'KISAO_0000019',  # default is CVODE
        },
        'time_step': 1.,
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
                algorithm=Algorithm(**self.parameters['algorithm']),
            )
        elif self.parameters['simulation'] == 'steady_state':
            simulation = SteadyStateSimulation(
                id='simulation',
                algorithm=Algorithm(**self.parameters['algorithm']),
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

        # pre-process
        self.sed_task_config = Config(LOG=False)
        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.outputs,
            config=self.sed_task_config,
        )

        # port assignments from parameters
        self.port_assignments = {}
        self.input_ports, input_assignments = self.get_port_assignment(
            self.parameters['input_ports'],
            self.inputs,
            self.parameters['default_input_port_name'],
        )
        self.port_assignments.update(input_assignments)
        self.output_ports, output_assignments = self.get_port_assignment(
            self.parameters['output_ports'],
            self.outputs,
            self.parameters['default_output_port_name'],
        )
        self.port_assignments.update(output_assignments)

        # TODO (ERAN) -- precalculate initial state, and use types for port_schema.
        #  get rid of default_output_value, default_input_value


    def get_port_assignment(
            self,
            ports_dict,
            variables,
            default_port_name,
    ):
        port_assignments = {}
        port_names = []
        all_variables = [input_state.id for input_state in variables]
        remaining_variables = copy.deepcopy(all_variables)
        if ports_dict:
            for port_id, variables in ports_dict.items():
                if isinstance(variables, str):
                    variables = [variables]
                for variable_id in variables:
                    assert variable_id in all_variables, \
                        f"'{variable_id}' is not in the available in variable ids: {all_variables} "
                    remaining_variables.remove(variable_id)
                port_assignments[port_id] = variables
                port_names.append(port_id)

        if remaining_variables:
            default_input_port_id = default_port_name
            port_assignments[default_input_port_id] = all_variables
            port_names.append(default_input_port_id)
        return port_names, port_assignments


    def initial_state(self, config=None):
        """
        extract initial state according to port_assignments
        """
        initial_state = {
            'global_time': 0
        }
        # TODO (ERAN) -- tellurium gets a str here, float() might not always apply
        input_values = {
            input_state.id: float(input_state.new_value)
            for input_state in self.inputs}

        # run task to view initial values
        # TODO (ERAN) -- can we get the initial output values without running a task?
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
                    # TODO (Eran) -- need more configurable input/output values.
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
            config=self.sed_task_config,
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
