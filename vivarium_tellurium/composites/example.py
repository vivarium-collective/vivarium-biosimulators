from vivarium.core.composer import Composer


class Example(Composer):

    def generate_topology(self, config):
        return {}

    def generate_processes(self, config):
        return {}
