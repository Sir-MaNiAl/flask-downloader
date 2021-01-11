def human_readable_size(size):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0:
            return f'{size:.4g} {unit}'
        size /= 1024.0
    return f'{size:4_.0d} {unit}'
