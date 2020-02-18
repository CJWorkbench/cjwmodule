from cjwmodule.testing.params import MockParams


def test_mock_factory_default():
    P = MockParams.factory(p=1, q=2)
    assert P() == {"p": 1, "q": 2}


def test_mock_factory_non_default():
    P = MockParams.factory()
    assert P(p=1, q=2) == {"p": 1, "q": 2}


def test_mock_factory_override():
    P = MockParams.factory(p=0, q=1)
    assert P(p=1, q=2) == {"p": 1, "q": 2}
