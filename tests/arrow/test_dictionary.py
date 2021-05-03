import pyarrow as pa

from cjwmodule.arrow.dictionary import recode_or_decode_dictionary


def assert_chunked_array_equals(
    actual: pa.ChunkedArray, expected: pa.ChunkedArray
) -> None:
    assert actual.to_pylist() == expected.to_pylist()
    assert actual.num_chunks == expected.num_chunks
    for actual_chunk, expected_chunk in zip(actual.chunks, expected.chunks):
        if hasattr(expected_chunk, "dictionary"):
            assert hasattr(actual_chunk, "dictionary")
            assert actual_chunk.dictionary == expected_chunk.dictionary
        else:
            assert not hasattr(expected_chunk, "dictionary")


def test_recode_or_decode_dictionary_decode_when_len_too_low():
    ca = pa.chunked_array([["a", "b", "c", None]], pa.utf8()).dictionary_encode()
    result = recode_or_decode_dictionary(ca)
    assert_chunked_array_equals(
        result, pa.chunked_array([["a", "b", "c", None]], pa.utf8())
    )


def test_recode_or_decode_dictionary_decode_when_all_null():
    ca = pa.chunked_array([[None, None]], pa.utf8()).dictionary_encode()
    result = recode_or_decode_dictionary(ca)
    assert_chunked_array_equals(result, pa.chunked_array([[None, None]], pa.utf8()))


def test_recode_or_decode_dictionary_decode_when_no_record_batches():
    ca = pa.chunked_array([], pa.utf8()).dictionary_encode()
    result = recode_or_decode_dictionary(ca)
    assert_chunked_array_equals(result, pa.chunked_array([], pa.utf8()))


def test_recode_or_decode_dictionary_multiple_chunks():
    ca = (
        pa.chunked_array([["a", "b", "a"], ["a", "c", "a"], ["d"]])
        .dictionary_encode()
        .slice(0, 6)
    )
    assert len(ca.chunks[0].dictionary) == 4
    result = recode_or_decode_dictionary(ca)
    assert_chunked_array_equals(
        result,
        pa.chunked_array(
            [["a", "b", "a"], ["a", "c", "a"]], pa.utf8()
        ).dictionary_encode(),
    )
    assert len(result.chunks[0].dictionary) == 3


def test_recode_or_decode_dictionary_valid_returns_input():
    expected = pa.chunked_array([["a", "b", "a", "a"]], pa.utf8()).dictionary_encode()
    actual = recode_or_decode_dictionary(expected)
    assert_chunked_array_equals(actual, expected)
    assert actual is expected  # identity!


def test_recode_or_decode_dictionary_nix_unused_value():
    ca = (
        pa.chunked_array([["a", "b", "a", "a", "a", "c"]])
        .dictionary_encode()
        .filter([True, True, True, True, True, False])
    )
    expected = pa.chunked_array([["a", "b", "a", "a", "a"]]).dictionary_encode()
    actual = recode_or_decode_dictionary(ca)
    assert_chunked_array_equals(actual, expected)


def test_recode_or_decode_dictionary_merge_duplicate_values():
    ca = pa.chunked_array(
        [
            pa.DictionaryArray.from_arrays(
                pa.array([0, 1, 1, 2, None]), pa.array(["a", "a", "b"])
            )
        ]
    )
    expected = pa.chunked_array([["a", "a", "a", "b", None]]).dictionary_encode()
    actual = recode_or_decode_dictionary(ca)
    assert_chunked_array_equals(actual, expected)
