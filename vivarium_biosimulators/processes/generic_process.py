import importlib
import copy
from typing import *
from dataclasses import dataclass
from vivarium.core.process import Process
from vivarium_biosimulators.library.process_logger import ProcessLogger
from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, ModelLanguage,
    UniformTimeCourseSimulation, SteadyStateSimulation
)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_outputs_for_simulation

TIME_COURSE_SIMULATIONS = ['uniform_time_course', 'analysis']


@dataclass
class SchemaSettings:
    _default: Union[int, float]
    _value: Any
    _updater: str
    _divider: str
    _emit: bool
    _serializer: Any
    _properties: Any


@dataclass
class SimulatorConfig:
    """
    Generic Configuration object for interfacing with the Simulator.

    ### Parameters:
    --------
    api:`str`
        Api from which the simulator originates.
    api_imports:`List[str, None]`
        Values to be imported from`api`.

    ### Returns:
    ---------
    `SimulatorConfig`
        Instance of a configuration object to be used as the default value for the `Process`.
    """
    api: str
    api_imports: Union[Tuple, List[Union[str, None]]]
    input_ports: Optional[Dict]
    output_ports: Optional[Dict]
    default_input_port_name: str
    default_output_port_name: str
    emit_ports: List[str]
    algorithm: Optional[Dict]
    sed_task_config: Optional[Dict]
    time_step: Optional[float]
    model_source: Optional[str]
    model_language: Optional[str]
    simulation: Optional[str]
    name: Optional[Any]
    _schema: Optional[Any]
    _parallel: Optional[bool]


class GenericSimulatorProcess(Process):
    """
    The following protocol is required for the `vivarium.core.processes.Process()` interface:
        * Constructor (`__init__`) method that accepts parameters and configs the model. Defaults to `defaults`.
        * ports_schema (`@classmethod`) which defines the variables that will be updated and "listened to".
        * next_update (`@classmethod`) that runs the model and returns an update.
    """

    defaults = {
        'api': '',
        'imports': {
            'api_imports': (),
            'primary_executer': '',
        },
        'input_ports': None,
        'output_ports': None,
        'default_input_port_name': 'inputs',
        'default_output_port_name': 'outputs',
        'emit_ports': ['outputs'],
    }

    def __init__(self,
                 parameters: Dict = None,
                 simulator_config: SimulatorConfig = None):
        """
        Generic instance of a `Process` that fits any simulator and its respective module.

        An Api value must be passed.

        ### Parameters:
        ---------------
        parameters: `Dict`
            Dictionary of parameters required for this instance. Defaults to `defaults` if there is no value passed and a `simulator_config` IS passed.
        simulator_config: `SimulatorConfig`
            Configuration object to be used in place of `parameters`. Defaults to `None`.

        ### Returns:
        ---------------
        `GenericSimulatorProcess`
            Instance of a generic process and thus the fulfillment of 1/3 of the `Process` interface (Constructor)

        """
        if not parameters and simulator_config:
            parameters = simulator_config.__dict__
        super().__init__(parameters)
        self.logger = ProcessLogger(dirpath='/Users/alex/Desktop/my_log')
        module = importlib.import_module(self.parameters['api'])
        self.__parse_module(module, *self.parameters['imports']['api_imports'])
        self.primary_executer = self.__set_primary_executer(self.parameters['imports']['primary_executer'], module)
        self.__assign_ports()

    def __set_attribute_from_params(self, content: str, module: object) -> None:
        """
        Set Process attributes with methods and/or content from given module.

        #### Parameters
        ---------------
        content: `str`
            module content which is also a `kwarg` of the `module` parameter to be loaded and assigned.
        module: `object(ModuleType)`
            module object loaded from `importlib.import_module`.

        """
        self.__setattr__(content, getattr(module, content))

    def __set_primary_executer(self, executer: str, module: object) -> None:
        """
        Use the `self.__set_attribute_from_params()` method to define what this process runs in the generic `self.run_task()` method.

        "Where the rubber meets the ground, the primary executer is found."

        #### Parameters
        ---------------
        executer: `str`
            name of the method to be defined as the primary executer.
        module: `object(ModuleType)`
            required argument which defines the origin of `executer`.

        #### Returns:
        -------------
        `None`
            sets the value of`self.executer`which is used as the primary logic(`function`) in the generic`self.run_task()`method.

        """
        self.__set_attribute_from_params(executer, module)

    def __parse_module(self, mod, *module_content) -> None:
        for content in module_content:
            self.__set_attribute_from_params(content, mod)

    def __assign_ports(self) -> None:
        """
        Implement Port Assignments.
        """
        self.port_assignments = {}
        self.input_ports, input_assignments = self.__assign_port('input')
        self.port_assignments.update(input_assignments)
        self.output_ports, output_assignments = self.__assign_port('output')
        self.port_assignments.update(output_assignments)

    def __assign_port(self, direction: str) -> Tuple:
        """
        Assign Individual Port.

        #### Parameters
        ----------
        direction: `str`
            Which port to assign. Value MUST be either `'input'` or `'output'`.

        #### Returns
        -------
        `Tuple[List, Dict]`
            the values for `port_names` and `port_assignments`
        """
        assert direction == 'input' or 'output'
        input_ports = self.parameters[f'{direction}_ports']
        input_variables = list(input_ports.values())
        input_port_name = self.parameters[f'default_{direction}_port_name']
        target_input_to_id = {}
        return self.__get_port_assignment(
            input_ports,
            input_variables,
            input_port_name,
            target_input_to_id
        )

    def __get_port_assignment(
        self,
        ports_dict: Dict,
        variables: List,
        default_port_name: str = None,
        target_to_id: Dict = {},
    ) -> Tuple:
        """
        Get port assignment values for given target (input or output).\n
        Args:\n
            * ports_dict`(Dict[str, Any])`: value originating from `self.parameters` for either :term:`input_ports` or :term:`output_ports`.\n
            * variables`(List[Dict])`: Variables that are to be listened to on given port.\n
            * default_port_name`(str)`: tag name for the input ports/variables. If no value is passed, defaults to :term:`self.parameters['default_input_port_name']`.\n
            * target_to_id`(Dict)`: target collection for id-ing. Defaults to `{}`.\n
        Returns:\n
            * `Tuple[port_names(List), port_assignments(Dict)  ]`: values for given port.
        """
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

    def ports_schema(self):
        """ 
        Make port schema for all ports and variables in self.port_assignments.

        ### Parameters
        ----------
        __self.port_assignments: `Dict`
            Inaccessible (from here) value of port assignments.

        ### Returns
        -----------
        schema: `Dict`
            The port_schema which listens to given variables and thus 1/3 of the requirement of the `Process` interface.
        """
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

    def get_delta(self, before, after):
        # TODO -- make this work for BioNetGen, MCell.
        # TODO -- different method for different data types
        return after - before

    def __get_primary_executer_signature(self) -> OrderedDict:
        import inspect
        return inspect.signature(self.primary_executer).parameters

    def run_task(self, *run_parameters):
        """
        Execute the primary simulator logic. 

        Arguments should be specific to those required by the primary execution logic of the given simulator.

        #### Parameters
        ----------
        **run_parameters: `kwargs: Any`
            parameters required to run a simulation method.

        #### Returns
        ------------
        `Any`
            whatever`type()`is returned by the primary execution logic aka`self.primary_executer()`and executer signature.

        #### Example
        -------
        In Tellurium core, the primary method with which roadrunner runs a simulation is `simulate`, which takes a start, end, and interval value.\n
        For Example:\n
            `r = te.loada('S1 -> S2; k1*S1; k1 = 0.1; S1 = 10')`\n
            `r.simulate(0, 50, 100)`\n
                        ^  ^    ^\n
                        here exist the `**run_parameters`.\n
        Thus in the case of Tellurium, the processes' `self.run_task()` method would return a `RoadRunner` array result object.
        """
        return self.primary_executer(*run_parameters)

    def next_update(self, state, *run_parameters):
        # collect the inputs
        input_values = {}
        for port_id in self.input_ports:
            input_values.update(state[port_id])

        # run task
        run_parameters_signature = self.__get_primary_executer_signature()
        raw_results = self.run_task(*run_parameters)

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
                    update[port_id][variable_id] = self.get_delta(
                        state[port_id][variable_id], value)

        log_entry = f'Next update of value: {update} generated.'
        self.logger.add_entry(log_entry)
        return update
