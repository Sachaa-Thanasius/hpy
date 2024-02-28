from hpy.universal import _debug

class HPyDebugError(Exception):
    pass

class HPyLeakError(HPyDebugError):
    def __init__(self, leaks):
        # type: (list[object]) -> None
        super().__init__()
        self.leaks = leaks

    def __str__(self):
        lines = []  # type: list[str]
        n = len(self.leaks)
        s = 's' if n != 1 else ''
        lines.append(f'{n} unclosed handle{s}:')
        for dh in self.leaks:
            lines.append('    %r' % dh)
        return '\n'.join(lines)


class LeakDetector:

    def __init__(self):
        self.generation = None  # type: int | None

    def start(self):
        # type: () -> None
        if self.generation is not None:
            raise ValueError('LeakDetector already started')
        self.generation = _debug.new_generation()

    def stop(self):
        # type: () -> None
        if self.generation is None:
            raise ValueError('LeakDetector not started yet')
        leaks = _debug.get_open_handles(self.generation)
        if leaks:
            raise HPyLeakError(leaks)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, etype, evalue, tb):
        # type: (object, object, object) -> None
        self.stop()
