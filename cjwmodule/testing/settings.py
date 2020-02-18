__all__ = ["MockSettings"]


class MockSettings:
    @staticmethod
    def factory(**kwargs):
        """Build a MockSettings factory with default values.

        Usage:

            S = MockSettings.factory(foo=3)
            settings = S(bar=2)  # settings.foo == 3, settings.bar == 2
        """

        def build(**d):
            settings = MockSettings()
            for setting, value in {**kwargs, **d}.items():
                setattr(settings, setting, value)
            return settings

        return build
