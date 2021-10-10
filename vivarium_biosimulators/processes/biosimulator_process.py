"""
====================
BioSimulator Process
====================

``BiosimulatorProcess`` is a general Vivarium :term:`process class` that can load any
BioSimulator and model, and run it.

References:
 * KISAO: https://bioportal.bioontology.org/ontologies/KISAO

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


def get_port_assignment(
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
        port_assignments[default_port_name] = remaining_variables
        port_names.append(default_port_name)
    return port_names, port_assignments


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
            native_data_types=True,
            native_ids=True,
        )

        # make an map of input ids to targets
        self.input_id_target_map = {}
        self.input_id_target_namespace = {}
        for variable in self.inputs:
            # self.input_id_target_map[variable.id] = variable.target
            var = variable.id
            if '_lower_bound' in var:
                var2 = var.replace('_lower_bound', '')
                self.input_id_target_map[
                    var] = f"/sbml:sbml/sbml:model/sbml:listOfReactions/sbml:reaction[@id='{var2}']/@fbc:lowerFluxBound"
            elif '_upper_bound' in var:
                var2 = var.replace('_upper_bound', '')
                self.input_id_target_map[
                    var] = f"/sbml:sbml/sbml:model/sbml:listOfReactions/sbml:reaction[@id='{var2}']/@fbc:upperFluxBound"
            else:
                self.input_id_target_map[variable.id] = variable.target
            self.input_id_target_namespace[variable.id] = variable.target_namespaces

        # TODO (ERAN) -- why do we need sed_outputs for preprocess_sed_task in tellurium?
        # assign outputs to task
        _, _, self.sed_outputs, _ = get_parameters_variables_outputs_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__,
            algorithm_kisao_id=simulation.algorithm.kisao_id,
        )
        for variable in self.sed_outputs:
            variable.task = self.task

        # pre-process
        self.sed_task_config = Config(LOG=False)
        self.preprocessed_task = self.preprocess()

        # port assignments from parameters
        default_input_port = self.parameters['default_input_port_name']
        self.port_assignments = {}
        self.input_ports, input_assignments = get_port_assignment(
            self.parameters['input_ports'],
            self.inputs,
            default_input_port,
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

    def initial_state(self, config=None):
        return self.saved_initial_state

    def make_initial_state(self):
        """
        extract initial state according to port_assignments
        """

        # get input values
        input_values = {
            input_state.id: input_state.new_value
            for input_state in self.inputs}

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
            schema[port_id] = {
                variable: {
                    '_default': self.saved_initial_state[port_id][variable],
                    '_updater': 'accumulate',
                    '_emit': emit_port,
                } for variable in variables
            }
        return schema

    def preprocess(self):
        preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.sed_outputs,
            config=self.sed_task_config,
        )
        return preprocessed_task

    def run_task(self, inputs, interval, initial_time=0.):

        # update model based on input
        self.task.changes = []
        for variable_id, variable_value in inputs.items():
            self.task.changes.append(ModelAttributeChange(
                target=self.input_id_target_map[variable_id],
                new_value=variable_value,
                target_namespaces=self.input_id_target_namespace[variable_id],
            ))

        # TODO -- optional reprocess?
        # self.preprocessed_task = self.preprocess()
        # if self.parameters['biosimulator_api'] == 'biosimulators_cobrapy':
        #     import ipdb; ipdb.set_trace()

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

                    # TODO (ERAN) -- different get_delta for different data types?
                    update[port_id][variable_id] = get_delta(
                        state[port_id][variable_id], value)
        return update
