
class ICoCoNameEnumMeta(type):

    def names(cls) -> list[str]:
        names = [
            val
            for var, val in cls.__dict__.items()
            if (not var.startswith("_") and isinstance(val, str))
        ]
        for base in cls.__bases__:
            if issubclass(base, ICoCoNameEnum):
                names.extend(base.names())
        return names

    def __iter__(cls):
        return iter(cls.names())

    def __contains__(cls, name):
        return name in cls.names()

    def __str__(cls):
        return f"{cls.__name__}={cls.names()}"


class ICoCoNameEnum(metaclass=ICoCoNameEnumMeta):
    """Enum-like class to easily iterate on ICoCo names.

    Example
    -------

    consider `["TOTO", "TATA", "TITI"]` as names which can be provided to a given ICoCo Problem.
    You may declare ::

        class InputDoubleEnum(ICoCoNameEnum):
            "Names avail for setInputDoubleValue"

            TOTO = "TOTO"
            TATA = "TATA"
            TUTU = "TETE"

        class InputFieldDoubleEnum(InputDoubleEnum):
            "Names avail for setInputMEDDoubleField (see also the setInputDoubleValue names)."

            TITI = "TITI"

    Which allows to easily iterate on those names in an ICoCo Problem ::

        class Problem:

            def setInputDoubleValue(name: str, value: float):
                if name not in InputDoubleEnum:
                    raise ...
                ...

            def setInputMEDDoubleField(name: str, value: float):
                if name not in InputFieldDoubleEnum:
                    raise ...
                ...

    """
    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a namespace, not an instance")
