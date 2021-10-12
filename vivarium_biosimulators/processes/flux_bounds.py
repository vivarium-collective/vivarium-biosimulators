"""
=====================
Flux Bounds Converter
=====================
"""
from vivarium.core.process import Process
from vivarium.library.units import units


def get_flux_and_bound_ids(flux_to_bound_map):
    """
    Args: flux_to_bound_map: dictionary with {flux: bounds}. Bounds can optionally
        be a dictionary with keys 'upper_bound', 'lower_bound', and 'range' to have a
        single reaction map to upper and lower bounds, which set the bounds to a range
        around the given reaction flux.
    Returns: flux_ids, bounds_ids
    """
    flux_ids = []
    bounds_ids = []
    for flux_id, bounds_id in flux_to_bound_map.items():
        flux_ids.append(flux_id)
        if isinstance(bounds_id, dict):
            bounds_ids.append(bounds_id['upper_bound'])
            bounds_ids.append(bounds_id['lower_bound'])
        else:
            bounds_ids.append(bounds_id)
    return flux_ids, bounds_ids


class FluxBoundsConverter(Process):
    """A wrapper for an ODE process

    Converts the ODE process's output fluxes to flux bounds inputs for an fba process.

    TODO (ERAN) mass and volume should come from a store so it can be updated
    """
    defaults = {
        'flux_to_bound_map': {},
        'ode_process': None,
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/L/s',
        'default_range': (0.95, 1.05),
        'time_unit': 's',
        'mass': (1, 'fg'),
        'volume': (1, 'fL'),
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)
        self.flux_to_bound_map = self.parameters['flux_to_bound_map']
        self.ode_process = self.parameters['ode_process']
        self.inputs = self.ode_process.inputs
        self.outputs = self.ode_process.outputs
        self.input_ports = self.ode_process.input_ports
        self.output_ports = self.ode_process.output_ports
        self.flux_ids, self.bounds_ids = get_flux_and_bound_ids(self.flux_to_bound_map)

        # unit conversion
        self.flux_unit = units(self.parameters['flux_unit'])
        self.bounds_unit = units(self.parameters['bounds_unit'])
        self.time_unit = units(self.parameters['time_unit'])
        self.mass = self.parameters['mass'][0] * units(self.parameters['mass'][1])
        self.volume = self.parameters['volume'][0] * units(self.parameters['volume'][1])

    def initial_state(self, config=None):
        state = self.ode_process.initial_state(config)
        state['bounds'] = {}
        return state

    def calculate_timestep(self, states):
        """
        Use the ODE process's timestep
        """
        return self.ode_process.calculate_timestep(states)

    def ports_schema(self):
        """
        Use the ODE process's ports, with an added 'bounds' port for flux bounds output.
        """
        ports = self.ode_process.get_schema()
        assert set(ports['fluxes']) <= set(self.flux_ids), 'all ode fluxes must be in flux_to_bound_map'
        ports['bounds'] = {
            rxn_id: {}
            for rxn_id in self.bounds_ids
        }
        return ports

    def convert_fluxes(self, fluxes, dt):
        """
        Divide by the time step to get flux bounds, and convert to bounds unit
        """
        flux_bounds = {}
        for flux_id, flux_value in fluxes.items():
            try:
                flux = (
                    flux_value / dt * (
                        self.flux_unit / self.time_unit)
                ).to(self.bounds_unit).magnitude
            except:
                # use mass?
                flux = (
                    flux_value * self.volume / self.mass / dt * (
                        self.flux_unit / self.time_unit)
                ).to(self.bounds_unit).magnitude

            bounds = self.flux_to_bound_map[flux_id]
            if isinstance(bounds, dict):
                upper_bound_id = bounds['upper_bound']
                lower_bound_id = bounds['lower_bound']
                bounds_range = bounds.get('range', self.parameters['default_range'])
                bound_values = (flux * bounds_range[0], flux * bounds_range[1])
                max_flux = max(bound_values)
                min_flux = min(bound_values)
                if flux <= 0:
                    flux_bounds[upper_bound_id] = 0
                    flux_bounds[lower_bound_id] = min_flux
                else:
                    flux_bounds[upper_bound_id] = max_flux
                    flux_bounds[lower_bound_id] = 0
                # print(f'BOUNDS: {bound_values}')
            else:
                flux_bounds[bounds] = flux

        return flux_bounds

    def next_update(self, interval, states):
        """
        Get the ODE process's update, convert the flux values to bounds,
        add them to the bounds port, and return the full update.
        """
        update = self.ode_process.next_update(interval, states)
        if update.get('fluxes'):
            bounds = self.convert_fluxes(update['fluxes'], interval)
            update['bounds'] = {
                flux_id: {
                    '_value': bound,
                    '_updater': 'set',
                } for flux_id, bound in bounds.items()
            }
        return update
