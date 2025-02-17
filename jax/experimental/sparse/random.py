# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import operator

from jax import vmap
from jax import random
from jax.util import split_list
import numpy as np
import jax.numpy as jnp
from jax.experimental import sparse


def random_bcoo(key, shape, *, dtype=jnp.float_, nse=0.2, n_batch=0, n_dense=0,
                unique_indices=True, generator=random.uniform, **kwds):
  """Generate a random BCOO matrix.

  Args:
    key : random.PRNGKey to be passed to ``generator`` function.
    shape : tuple specifying the shape of the array to be generated.
    dtype : dtype of the array to be generated.
    nse : number of specified elements in the matrix, or if 0 < nse < 1, a
      fraction of sparse dimensions to be specified (default: 0.2).
    n_batch : number of batch dimensions. must satisfy ``n_batch >= 0`` and
      ``n_batch + n_dense <= len(shape)``.
    n_dense : number of batch dimensions. must satisfy ``n_dense >= 0`` and
      ``n_batch + n_dense <= len(shape)``.
    unique_indices : boolean specifying whether indices should be unique
      (default: True).
    generator : function for generating random values accepting a key, shape, and
      dtype. It defaults to :func:`jax.random.uniform`, and may be any function
      with a similar signature.
    **kwds : additional keyword arguments to pass to ``generator``.

  Returns:
    arr : a sparse.BCOO array with the specified properties.
  """
  shape = tuple(map(operator.index, shape))
  n_batch = operator.index(n_batch)
  n_dense = operator.index(n_dense)
  if n_batch < 0 or n_dense < 0 or n_batch + n_dense > len(shape):
    raise ValueError(f"Invalid n_batch={n_batch}, n_dense={n_dense} for shape={shape}")
  n_sparse = len(shape) - n_batch - n_dense
  batch_shape, sparse_shape, dense_shape = map(tuple, split_list(shape, [n_batch, n_sparse]))
  batch_size = np.prod(batch_shape)
  sparse_size = np.prod(sparse_shape)
  if not 0 <= nse < sparse_size:
    raise ValueError(f"got nse={nse}, expected to be between 0 and {sparse_size}")
  if 0 < nse < 1:
    nse = int(np.ceil(nse * sparse_size))
  nse = operator.index(nse)

  data_shape = batch_shape + (nse,) + dense_shape
  indices_shape = batch_shape + (nse, n_sparse)

  @vmap
  def _indices(key):
    if not sparse_shape:
      return jnp.empty((nse, n_sparse), dtype=int)
    flat_ind = random.choice(key, sparse_size, shape=(nse,), replace=not unique_indices)
    return jnp.column_stack(jnp.unravel_index(flat_ind, sparse_shape))

  keys = random.split(key, batch_size + 1)
  data_key, index_keys = keys[0], keys[1:]
  data = generator(data_key, shape=data_shape, dtype=dtype, **kwds)
  indices = _indices(index_keys).reshape(indices_shape)

  return sparse.BCOO((data, indices), shape=shape)
