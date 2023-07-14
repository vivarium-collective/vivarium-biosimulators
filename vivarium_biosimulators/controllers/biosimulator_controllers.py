from enum import Enum
from typing import *
import os
import tellurium as te


class SimulationLogger:
    def __init__(self,
                 dirpath: str = '/content/tellurium_test_logs',
                 logname: str = 'log.json'):
        self.dirpath = dirpath
        self._handle_logging_dir(self.dirpath)
        self.log_filepath = os.path.join(self.dirpath, logname)
        self.log = self.read_log()

    def _handle_logging_dir(self, dirpath: str):
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)

    def read_log(self) -> dict:
        from json import load
        if not len(os.listdir(self.dirpath)):
            return {}
        else:
            with open(self.log_filepath, 'r') as f:
                return load(f)

    def add_entry(self, entry):
        from datetime import datetime
        key = datetime.now().strftime('%D_%T').replace(':', '_').replace('/', '-')
        self.log[key] = [entry]

    def flush_log(self):
        self.log.clear()


class SimulatorProtocol:
    def __init__(self, framework_id: str, model: str, use_logging: bool, logger: SimulationLogger):
        raise NotImplemented

    def _get_framework(self):
        raise NotImplemented

    def _get_logger(self, log_dirpath: str, log_filename: str) -> SimulationLogger:
        raise NotImplemented

    def get_metadata(self) -> Dict:
        raise NotImplemented


class TelluriumIntegratorNames(str, Enum):
    cvode = 'cvode'
    gillespie = 'gillespie'
    rk = 'rk4'


class TelluriumIntegratorProtocol:
    def __init__(self, name: str):
        raise NotImplemented

    def get_settings(self) -> Dict:
        raise NotImplemented


class CvodeIntegrator:
    def __init__(self,
                 variable_step_size: Optional[bool] = False,
                 stiff: Optional[bool] = False,
                 absolute_tolerance: Optional[Union[int, float]] = 0,
                 relative_tolerance: Optional[Union[int, float]] = 0):
        self.variable_step_size = variable_step_size
        self.stiff = stiff
        self.absolute_tolerance = absolute_tolerance
        self.relative_tolerance = relative_tolerance


class TelluriumIntegrator(TelluriumIntegratorProtocol):
    def __init__(self, name: str, *values):
        self.settings = self.get_settings(name)

    def get_settings(self, name: str, *values):
        if 'cvode' in name:
            return CvodeIntegrator(values)


integrator = TelluriumIntegrator(name='cvode')


class TelluriumSimulator(SimulatorProtocol):
    def __init__(self,
                 model: str,
                 model_type: str,
                 use_logging: bool = True,
                 integrator: TelluriumIntegrator = None,
                 logger: SimulationLogger = None):
        self.__set_framework()
        self.__set_logger(use_logging)
        self.model = model
        self.model_type = model_type
        self.integrator = integrator
        self.roadrunner_model = self.parse_model_type()
        self.metadata = self.get_metadata()

    def _set_framework(self):
        self.framework_id = 'tellurium'

    def _set_logger(self, use_logging: bool):
        self.logger = SimulationLogger() if use_logging else None

    def parse_model_type(self):
        return te.loada(self.model) if 'antimony' in self.model_type else None

    def get_metadata(self):
        return {'model': [self.model],
                'model_type': [self.model_type],
                'integrator': [self.integrator],
                'roadrunner_model': [self.roadrunner_model]}


class ControllerProtocol:
    def __init__(self, simulator: Union[SimulatorProtocol, List[SimulatorProtocol]], next_process=None):
        raise NotImplementedError

    def get_simulator(self, i: int = 0) -> SimulatorProtocol:
        raise NotImplementedError

    def get_smi(self, simulator: Union[SimulatorProtocol, List[SimulatorProtocol]]) -> Dict:
        raise NotImplementedError

    def emit_smi(self):
        raise NotImplementedError


class ProcessController(ControllerProtocol):
    def __init__(self,
                 simulator: Union[SimulatorProtocol, List[SimulatorProtocol]],
                 input_emitter: ControllerProtocol = None,
                 output_reciever: ControllerProtocol = None,
                 next_process=None):
        ...


class TelluriumController(ProcessController):
    def __init__(self,
                 simulator: Union[TelluriumSimulator, List[TelluriumSimulator]],
                 input_emitter: Optional[ProcessController] = None,
                 output_reciever: Optional[ProcessController] = None,
                 next_process=None):
        '''
            Creates a new simulator controller instance.
                Args:
                    :param:`simulator`::`(SimulatorProtocol | List[SimulatorProtocol])`:
                        simulator(s) for the process\n
                    :param:`input_emitter`::`(ProcessControllerProtocol | None)`:
                        controller of previous process that this controller is listening to. Defaults to `None`\n
                    :param:`output_reciever`::`(ProcessControllerProtocol | None)`:
                        controller of next process that this controller is giving information to. Defaults to `None`\n
                    :param:`next_process`::`(str)`:
                        id of the next vivarium node. Defaults to `None`.
        '''
        self.simulator = simulator
        self.adjacent_controllers = self.get_adjacent_controllers(input_emitter, output_reciever)

    def get_adjacent_controllers(self,
                                 input: Union[ProcessController, None],
                                 output: Union[ProcessController, None]) -> Dict:
        return {'input_emitter': input,
                'output_reciever': output}


test_model = """
    model test
        compartment C1;
        C1 = 1.0;
        species S1, S2;

        S1 = 10.0;
        S2 = 0.0;
        S1 in C1; S2 in C1;
        J1: S1 -> S2; k1*S1;

        k1 = 1.0;
    end
    """

basic_cvode_integrator_head = TelluriumIntegrator('cvode')
basic_simulator_head = TelluriumSimulator(model=test_model,
                                          model_type='antimony',
                                          integrator=basic_cvode_integrator)

basic_controller_head = TelluriumController(basic_simulator)
basic_controller_head.adjacent_controllers


class BioSimProcessNode:
    def __init__(self, simulator, controller, integrator):
        raise NotImplemented

    def get_metadata(self) -> Dict:
        raise NotImplemented


class TelluriumProcessNode(BioSimProcessNode):
    def __init__(self,
                 simulator: TelluriumSimulator,
                 controller: TelluriumController,
                 integrator: TelluriumIntegrator = None,
                 next_node=None):
        self.simulator = simulator
        self.controller = controller
        self.next_node = next_node
        self.metadata = self.get_metadata()

    def get_metadata(self) -> Dict:
        return {'simulator': self.simulator,
                'controller': self.controller,
                'next_node': self.next_node}


m1 = 'basic simulation just created!'
basic_simulator_head.logger.add_entry(m1)
basic_simulator_head.logger.log
basic_simulator_head.logger.flush_log()
basic_simulator_head.logger.log
basic_controller_head = TelluriumController(simulator=basic_simulator_head,
                                            input_emitter=None)
basic_process_node = TelluriumProcessNode(basic_simulator_head, basic_controller_head, next_node=None)

basic_process_node.metadata


class Graph:
    def __init__(self, max_nodes: int, num_edges: int):
        self.edges
