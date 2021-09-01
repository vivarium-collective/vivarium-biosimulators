from vivarium.core.composer import Composer



class Example(Composer):

    def generate_topology(self, config: Optional[dict]) -> Topology:
        return {}

    def generate_processes(
            self,
            config: Optional[dict]) -> Processes:
        return {}