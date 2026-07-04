def fire_grid_slice(fire_grid_bound: int) -> slice:
    if fire_grid_bound < 0:
        raise ValueError("fire_grid_bound must be >= 0")
    return slice(fire_grid_bound, -fire_grid_bound) if fire_grid_bound else slice(None)
