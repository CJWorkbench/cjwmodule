from cjwmodule.testing.settings import MockSettings


def test_mock_factory_default():
    S = MockSettings.factory(p=1, q=2)
    settings = S()
    assert settings.p == 1
    assert settings.q == 2


def test_mock_factory_non_default():
    S = MockSettings.factory()
    settings = S(p=1, q=2)
    assert settings.p == 1
    assert settings.q == 2


def test_mock_factory_override():
    S = MockSettings.factory(p=0, q=1)
    settings = S(p=1, q=2)
    assert settings.p == 1
    assert settings.q == 2
