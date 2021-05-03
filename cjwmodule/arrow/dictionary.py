import numpy as np
import pyarrow as pa


def _recode(
    array: pa.DictionaryArray, mapping: pa.DictionaryArray
) -> pa.DictionaryArray:
    """Return a clone of `array` with `mapping.dictionary` as its dictionary."""
    indices = mapping.indices.take(array.indices)
    return pa.DictionaryArray.from_arrays(indices, mapping.dictionary)


def recode_or_decode_dictionary(chunked_array: pa.ChunkedArray) -> pa.ChunkedArray:
    """Remove unused/duplicate dictionary values from -- or cast to pa.utf8().

    Workbench disallows unused/duplicate values. Call this function after
    filtering or modifying dictionary values: it returns a valid Workbench
    column given a valid Arrow column.

    Convert to utf8() if dictionary encoding is "bad". ("Bad" currently means,
    "each value is only used once;" but the meaning may change between minor
    versions.)

    Return `chunked_array` if it is already Workbench-valid and dictionary
    encoding is not "bad".
    """
    if chunked_array.num_chunks == 0:
        return pa.chunked_array([], pa.utf8())

    # if chunked_array.num_chunks != 1:
    #     chunked_array = chunked_array.unify_dictionaries()

    if len(chunked_array) - chunked_array.null_count <= len(
        chunked_array.chunks[0].dictionary
    ):
        return chunked_array.cast(pa.utf8())

    dictionary = chunked_array.chunks[0].dictionary

    used = np.zeros(len(dictionary), dtype=bool)
    for chunk in chunked_array.chunks:
        used[
            pa.compute.filter(
                chunk.indices, pa.compute.is_valid(chunk.indices)
            ).to_numpy()
        ] = True

    if not np.all(used):
        # Nix unused values; then scan for dups
        mapping = dictionary.filter(pa.array(used, pa.bool_())).dictionary_encode()
        need_recode = True
    else:
        # Scan for dups
        mapping = dictionary.dictionary_encode()
        need_recode = len(mapping.dictionary) < len(dictionary)

    if need_recode:
        chunks = [_recode(chunk, mapping) for chunk in chunked_array.chunks]
        return pa.chunked_array(chunks)

    return chunked_array
