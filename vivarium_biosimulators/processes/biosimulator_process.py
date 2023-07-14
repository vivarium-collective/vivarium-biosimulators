"""
====================
BioSimulator Process
====================

``Biosimulator`` is a general Vivarium :term:`process class` that can load any
BioSimulator and model, and run it.

References:
 * KISAO: https://bioportal.bioontology.org/ontologies/KISAO

"""

import importlib
import copy
from typing import *
from vivarium.core.process import Process
from vivarium_biosimulators.library.process_logger import ProcessLogger
from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, ModelLanguage,
    UniformTimeCourseSimulation, SteadyStateSimulation
)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_outputs_for_simulation

TIME_COURSE_SIMULATIONS = ['uniform_time_course', 'analysis']


def get_delta(before, after):
    # TODO -- make this work for BioNetGen, MCell.
    # TODO -- different method for different data types
    return after - before


def get_port_assignment(
        ports_dict,
        variables,
        default_port_name,
        target_to_id={},
):
    port_assignments = {}
    port_names = []
    all_variables = [
        target_to_id.get(var.target, var.id)
        for var in variables
    ]
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
        port_assignments[default_port_name] = remaining_variables
        port_names.append(default_port_name)
    return port_names, port_assignments


class Biosimulator(Process):
    """ A Vivarium wrapper for any BioSimulator

    Config:
        - biosimulator_api (str): the name of the imported biosimulator api.
        - model_source (str): a path to the model file.
        - model_language (str): the model language, select from biosimulators_utils.sedml.data_model.ModelLanguage.
        - simulation (str): select from ['uniform_time_course', 'steady_state', 'one_step', 'analysis'].
        - input_ports (dict): a dictionary mapping {'input_port_name': ['list', 'of', 'variables']}.
        - output_ports (dict): a dictionary mapping {'output_port_name': ['list', 'of', 'variables']}.
        - default_input_port_name (str): the default input port for variables not specified by input_ports.
        - default_output_port_name (str): the default output port for variables not specified by output_ports.
        - emit_ports (list): a list of the ports whose values are emitted.
        - algorithm (dict): the kwargs for biosimulators_utils.sedml.data_model.Algorithm.
        - sed_task_config (dict): the kwargs for biosimulators_utils.config.Config.
        - time_step (float): the synchronization time step.
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
        'emit_ports': ['outputs'],
        'algorithm': {
            'kisao_id': 'KISAO_0000019',  # default is CVODE
        },
        'sed_task_config': {
            'LOG': False,
        },
        'time_step': 1.,
    }

    def __init__(self, parameters: Dict = None):
        super().__init__(parameters)
        # Establish logger
        logging_dirpath = '/Users/alex/Desktop/vivarium_logs/vivarium_biosimulators_logs'
        self.logger = ProcessLogger(logging_dirpath, 'vivarium_biosimulators_log.json')
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
            native_data_types=True,
            native_ids=True,
            change_level=Task,
            # model_language_options={
            #     ModelLanguage.SBML: {
            #         'include_reaction_fluxes_in_kinetic_simulation_variables': False,
            #     }}
        )

        # TODO (ERAN) -- go through inputs and outputs, assign ids, use targets for meaning
        if not self.outputs[0].id:
            self.outputs[0].id = 'time'

        ###################################
        # Prepare model attribute changes #
        ###################################

        # find unique and repeat input ids
        repeat_ids = []
        unique_ids = []
        for variable in self.inputs:
            variable_id = variable.id
            if variable_id in repeat_ids:
                continue
            elif variable_id in unique_ids:
                unique_ids.remove(variable_id)
                repeat_ids.append(variable_id)
            else:
                unique_ids.append(variable_id)

        # get suggested input names for repeat ids
        suggested_inputs, _, _, _ = get_parameters_variables_outputs_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__,
            algorithm_kisao_id=simulation.algorithm.kisao_id,
            change_level=Task,
        )
        target_to_suggested_input_ids = {
            i.target: i.id for i in suggested_inputs}

        # make the map of input ids to targets
        self.input_target_map = {}
        self.input_target_namespace = {}
        self.input_initial_value = {}
        target_to_input_id = {}
        for variable in self.inputs:
            variable_id = variable.id
            target = variable.target
            if variable_id in repeat_ids:
                # if repeat, then use suggested id
                variable_id = target_to_suggested_input_ids[target]
            target_to_input_id[target] = variable_id
            self.input_target_map[variable_id] = target
            self.input_target_namespace[variable_id] = variable.target_namespaces
            self.input_initial_value[variable_id] = variable.new_value

        ##################
        # Pre-processing #
        ##################

        # map outputs to task
        for variable in self.outputs:
            variable.task = self.task

        # map inputs for pre-processing
        self.task.model.changes = []
        for variable in self.inputs:
            self.task.model.changes.append(ModelAttributeChange(
                target=variable.target,
                target_namespaces=variable.target_namespaces,
            ))

        # pre-process
        self.sed_task_config = Config(
            **self.parameters['sed_task_config'])
        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.outputs,
            config=self.sed_task_config,
        )

        ####################
        # Port Assignments #
        ####################

        # port assignments from parameters
        default_input_port = self.parameters['default_input_port_name']
        self.port_assignments = {}
        self.input_ports, input_assignments = get_port_assignment(
            self.parameters['input_ports'],
            self.inputs,
            default_input_port,
            target_to_input_id,
        )
        self.port_assignments.update(input_assignments)
        self.output_ports, output_assignments = get_port_assignment(
            self.parameters['output_ports'],
            self.outputs,
            self.parameters['default_output_port_name'],
        )
        self.port_assignments.update(output_assignments)

        # pre-calculate initial state
        # it is used to determine variable types in port_schema
        self.saved_initial_state = self.make_initial_state()

        log_entry = f'Biosimulator process with parameters: {self.parameters} created.'
        self.logger.add_entry(log_entry)

    def initial_state(self, config=None):
        return self.saved_initial_state

    def make_initial_state(self):
        """
        extract initial state according to port_assignments
        """

        # get input values
        input_values = self.input_initial_value

        # get output_values
        results = self.run_task(
            input_values, self.parameters['time_step'])
        output_values = self.process_results(
            results, time_course_index=0)

        initial_state = {}
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

        log_entry = f'Initial state with value: {initial_state} created.'
        self.logger.add_entry(log_entry)
        return initial_state

    def is_deriver(self):
        if self.parameters['simulation'] in TIME_COURSE_SIMULATIONS:
            return False
        return True

    def ports_schema(self):
        """ make port schema for all ports and variables in self.port_assignments """
        schema = {}
        for port_id, variables in self.port_assignments.items():
            emit_port = port_id in self.parameters['emit_ports']
            updater_schema = {'_updater': 'accumulate'} if port_id in self.output_ports else {}
            schema[port_id] = {
                variable: {
                    '_default': self.saved_initial_state[port_id][variable],
                    '_emit': emit_port,
                    **updater_schema,
                } for variable in variables
            }

        log_entry = f'Port schema with the value: {schema} created.'
        self.logger.add_entry(log_entry)
        return schema

    def run_task(self, inputs, interval, initial_time=0.):
        # update model based on input
        self.task.model.changes = []
        for variable_id, variable_value in inputs.items():
            self.task.model.changes.append(ModelAttributeChange(
                target=self.input_target_map[variable_id],
                new_value=variable_value,
                target_namespaces=self.input_target_namespace[variable_id],
            ))

        # set the simulation time
        self.task.simulation.initial_time = initial_time
        self.task.simulation.output_start_time = initial_time
        self.task.simulation.output_end_time = initial_time + interval

        try:
            # execute step
            raw_results, log = self.exec_sed_task(
                self.task,
                self.outputs,
                preprocessed_task=self.preprocessed_task,
                config=self.sed_task_config,
            )
            log_entry = f'Raw results: {raw_results} successfully generated.'
            self.logger.add_entry(log_entry)
            self.logger.write_log()
            return raw_results
        except Exception as e:
            log_entry = f'The exception: {e} was raised while generating raw results.'
            self.logger.add_entry(log_entry)
            self.logger.write_log()

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

    def next_update(self, interval, state):
        # collect the inputs
        input_values = {}
        for port_id in self.input_ports:
            input_values.update(state[port_id])

        # run task
        raw_results = self.run_task(input_values, interval)

        # transform results
        update = {}
        for port_id in self.output_ports:
            variable_ids = self.port_assignments[port_id]
            if variable_ids:
                update[port_id] = {}
                for variable_id in variable_ids:
                    raw_result = raw_results[variable_id]
                    value = self.process_result(raw_result)

                    # different get_delta for different data types?
                    update[port_id][variable_id] = get_delta(
                        state[port_id][variable_id], value)

        log_entry = f'Next update of value: {update} generated.'
        self.logger.add_entry(log_entry)
        return update
