"""
Execute by running: ``python vivarium_biosimulators/processes/biosimulators_process.py``

KISAO: https://bioportal.bioontology.org/ontologies/KISAO
"""
import importlib
import copy

from vivarium.core.process import Process
from vivarium.core.composition import simulate_process
from vivarium.core.control import run_library_cli

from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, 
    UniformTimeCourseSimulation, SteadyStateSimulation, ModelLanguage
)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_outputs_for_simulation


def get_delta(before, after):
    return after - before


class BiosimulatorsProcess(Process):
    """ A Vivarium wrapper for any BioSimulator

    parameters:
        - biosimulator_api (str): the name of the imported biosimulator api
        - model_source (str): a path to the model file
        - model_source (str):
        - simulation (str): select from 'uniform_time_course', 'steady_state', 'one_step', 'analysis'
        - input_ports (dict):
        - output_ports (dict):
        - default_input_port (str):
        - default_output_port (str):
        - emit_ports (list): a list of the ports whose values are emitted
        - time_step (float): the syncronization time step
    """
    
    defaults = {
        'biosimulator_api': '',
        'model_source': '',
        'model_language': '',
        'simulation': 'uniform_time_course',
        'input_ports': None,
        'output_ports': None,
        'default_input_port': 'inputs',
        'default_output_port': 'outputs',
        'emit_ports': ['outputs'],
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
        if self.parameters['simulation'] == 'uniform_time_course':
            simulation = UniformTimeCourseSimulation(
                id='simulation',
                initial_time=0.,
                output_start_time=0.,
                number_of_points=1,
                output_end_time=self.parameters['time_step'],
                algorithm=Algorithm(kisao_id='KISAO_0000019'),
            )
        elif self.parameters['simulation'] == 'steady_state':
            simulation = SteadyStateSimulation(
                id='simulation',
                algorithm=Algorithm(kisao_id='KISAO_0000437'),
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
        all_inputs = [input_state.id for input_state in self.inputs]
        all_outputs = [output_state.id for output_state in self.outputs]
        remaining_inputs = copy.deepcopy(all_inputs)
        remaining_outputs = copy.deepcopy(all_outputs)

        self.port_assignments = {}
        self.input_ports = []
        self.output_ports = []

        if self.parameters['input_ports']:
            for port_id, variables in self.parameters['input_ports'].items():
                if isinstance(variables, str):
                    variables = [variables]
                for variable_id in variables:
                    assert variable_id in all_inputs, \
                        f"port assigments: {variable_id} is not in the inputs {all_inputs} "
                    remaining_inputs.remove(variable_id)
                self.port_assignments[port_id] = variables
                self.input_ports.append(port_id)

        if remaining_inputs:
            default_input_port_id = self.parameters['default_input_port']
            self.port_assignments[default_input_port_id] = remaining_inputs
            self.input_ports.append(default_input_port_id)

        if self.parameters['output_ports']:
            for port_id, variables in self.parameters['output_ports'].items():
                if isinstance(variables, str):
                    variables = [variables]
                for variable_id in variables:
                    assert variable_id in all_outputs, \
                        f"port assigments: {variable_id} is not in the outputs {all_outputs} "
                    remaining_outputs.remove(variable_id)
                self.port_assignments[port_id] = variables
                self.output_ports.append(port_id)

        if remaining_outputs:
            default_output_port_id = self.parameters['default_output_port']
            self.port_assignments[default_output_port_id] = remaining_outputs
            self.output_ports.append(default_output_port_id)

    def initial_state(self, config=None):
        """extract initial state according to port_assignments

        TODO -- output states are 0 by default, need to extract them from self.outputs
        """
        initial_state = {}
        input_values = {
            input_state.id: input_state.new_value
            for input_state in self.inputs}

        for port_id, variables in self.port_assignments.items():
            if port_id in self.input_ports:
                initial_state[port_id] = {
                    variable: input_values[variable]
                    for variable in variables
                }
            elif port_id in self.output_ports:
                initial_state[port_id] = {
                    variable: 0
                    for variable in variables
                }
        return initial_state

    def is_deriver(self):
        if self.parameters['simulation'] == 'one_step':
            return True
        return False

    def ports_schema(self):
        schema = {
            'global_time': {'_default': 0.}
        }
        for port_id, variables in self.port_assignments.items():
            emit_port = port_id in self.parameters['emit_ports']
            schema[port_id] = {
                variable: {
                    '_default': 0.,
                    '_updater': 'accumulate',
                    '_emit': emit_port,
                } for variable in variables
            }
        return schema

    def next_update(self, interval, states):

        # collect the inputs
        input_variables = {}
        for port_id in self.input_ports:
            input_variables.update(states[port_id])

        # update model based on input
        self.task.changes = []
        for variable_id, variable_value in input_variables.items():
            self.task.changes.append(ModelAttributeChange(
                target=self.input_id_target_map[variable_id],
                new_value=variable_value,
            ))

        # set the simulation time
        global_time = states['global_time']
        self.task.simulation.initial_time = global_time
        self.task.simulation.output_start_time = global_time
        self.task.simulation.output_end_time = global_time + interval

        # execute step
        raw_results, log = self.exec_sed_task(
            self.task,
            self.outputs,
            preprocessed_task=self.preprocessed_task,
            config=self.config,
        )

        # transform results
        update = {}
        for port_id in self.output_ports:
            variable_ids = self.port_assignments[port_id]
            update[port_id] = {
                variable_id: get_delta(
                    states[port_id][variable_id],
                    raw_results[variable_id][-1])
                for variable_id in variable_ids
            }
        return update


def test_biosimulators_process(
        biosimulator_api='',
        model_source='',
        model_language=ModelLanguage.SBML.value,
        simulation='uniform_time_course',
        initial_state=None,
        input_output_map=None,
        total_time=10.,
):
    import warnings; warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': biosimulator_api,
        'model_source': model_source,
        'model_language':  model_language,
        'simulation': simulation,
    }
    process = BiosimulatorsProcess(config)

    # make a topology
    topology = {
        'global_time': ('global_time',),
        'input': ('state',) if not input_output_map else {
            **{'_path': ('state',)},
            **input_output_map,
        },
        'output': ('state',)
    }

    # get initial_state
    initial_state = initial_state or {}
    initial_model_state = {'state': initial_state} or process.initial_state()

    # run the simulation
    sim_settings = {
        'topology': topology,
        'total_time': total_time,
        'initial_state': initial_model_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

    return output


test_library = {
    '0': test_biosimulators_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/processes/biosimulators_process.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
