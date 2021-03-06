# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import pickle as pkl

from mxnet.ndarray import NDArray
from mxnet.test_utils import *
from numpy.testing import assert_allclose
import numpy.random as rnd

from mxnet.ndarray.sparse import RowSparseNDArray, CSRNDArray


def assert_fcompex(f, *args, **kwargs):
    prev_val = mx.test_utils.set_env_var("MXNET_EXEC_STORAGE_FALLBACK", "0", "1")
    f(*args, **kwargs)
    mx.test_utils.set_env_var("MXNET_EXEC_STORAGE_FALLBACK", prev_val)


def sparse_nd_ones(shape, stype):
    return mx.nd.ones(shape).tostype(stype)


def check_sparse_nd_elemwise_binary(shapes, stypes, f, g):
    # generate inputs
    nds = []
    for i, stype in enumerate(stypes):
        if stype == 'row_sparse':
            nd, _ = rand_sparse_ndarray(shapes[i], stype)
        elif stype == 'default':
            nd = mx.nd.array(random_arrays(shapes[i]), dtype = np.float32)
        else:
            assert(False)
        nds.append(nd)
    # check result
    test = f(nds[0], nds[1])
    assert_almost_equal(test.asnumpy(), g(nds[0].asnumpy(), nds[1].asnumpy()))


def test_sparse_nd_elemwise_add():
    num_repeats = 10
    g = lambda x,y: x + y
    op = mx.nd.elemwise_add
    for i in range(num_repeats):
        shape = [rand_shape_2d()] * 2
        assert_fcompex(check_sparse_nd_elemwise_binary,
                       shape, ['default'] * 2, op, g)
        assert_fcompex(check_sparse_nd_elemwise_binary,
                       shape, ['default', 'row_sparse'], op, g)
        assert_fcompex(check_sparse_nd_elemwise_binary,
                       shape, ['row_sparse', 'row_sparse'], op, g)


def test_sparse_nd_copy():
    def check_sparse_nd_copy(from_stype, to_stype, shape):
        from_nd = rand_ndarray(shape, from_stype)
        # copy to ctx
        to_ctx = from_nd.copyto(default_context())
        # copy to stype
        to_nd = rand_ndarray(shape, to_stype)
        to_nd = from_nd.copyto(to_nd)
        assert np.sum(np.abs(from_nd.asnumpy() != to_ctx.asnumpy())) == 0.0
        assert np.sum(np.abs(from_nd.asnumpy() != to_nd.asnumpy())) == 0.0

    shape = rand_shape_2d()
    shape_3d = rand_shape_3d()
    stypes = ['row_sparse', 'csr']
    for stype in stypes:
        check_sparse_nd_copy(stype, 'default', shape)
        check_sparse_nd_copy('default', stype, shape)
    check_sparse_nd_copy('row_sparse', 'row_sparse', shape_3d)
    check_sparse_nd_copy('row_sparse', 'default', shape_3d)
    check_sparse_nd_copy('default', 'row_sparse', shape_3d)

def test_sparse_nd_basic():
    def check_sparse_nd_basic_rsp():
        storage_type = 'row_sparse'
        shape = rand_shape_2d()
        nd, (v, idx) = rand_sparse_ndarray(shape, storage_type)
        assert(nd._num_aux == 1)
        assert(nd.indices.dtype == np.int64)
        assert(nd.stype == 'row_sparse')

    check_sparse_nd_basic_rsp()


def test_sparse_nd_setitem():
    def check_sparse_nd_setitem(stype, shape, dst):
        x = mx.nd.zeros(shape=shape, stype=stype)
        x[:] = dst
        dst_nd = mx.nd.array(dst) if isinstance(dst, (np.ndarray, np.generic)) else dst
        assert same(x.asnumpy(), dst_nd.asnumpy())

    shape = rand_shape_2d()
    for stype in ['row_sparse', 'csr']:
        # ndarray assignment
        check_sparse_nd_setitem(stype, shape, rand_ndarray(shape, 'default'))
        check_sparse_nd_setitem(stype, shape, rand_ndarray(shape, stype))
        # numpy assignment
        check_sparse_nd_setitem(stype, shape, np.ones(shape))


def test_sparse_nd_slice():
    def check_sparse_nd_csr_slice(shape):
        stype = 'csr'
        A, _ = rand_sparse_ndarray(shape, stype)
        A2 = A.asnumpy()
        start = rnd.randint(0, shape[0] - 1)
        end = rnd.randint(start + 1, shape[0])
        assert same(A[start:end].asnumpy(), A2[start:end])
        assert same(A[start:].asnumpy(), A2[start:])
        assert same(A[:end].asnumpy(), A2[:end])

    shape = (rnd.randint(2, 10), rnd.randint(1, 10))
    check_sparse_nd_csr_slice(shape)


def test_sparse_nd_equal():
    for stype in ['row_sparse', 'csr']:
        shape = rand_shape_2d()
        x = mx.nd.zeros(shape=shape, stype=stype)
        y = sparse_nd_ones(shape, stype)
        z = x == y
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = 0 == x
        assert (z.asnumpy() == np.ones(shape)).all()


def test_sparse_nd_not_equal():
    for stype in ['row_sparse', 'csr']:
        shape = rand_shape_2d()
        x = mx.nd.zeros(shape=shape, stype=stype)
        y = sparse_nd_ones(shape, stype)
        z = x != y
        assert (z.asnumpy() == np.ones(shape)).all()
        z = 0 != x
        assert (z.asnumpy() == np.zeros(shape)).all()


def test_sparse_nd_greater():
    for stype in ['row_sparse', 'csr']:
        shape = rand_shape_2d()
        x = mx.nd.zeros(shape=shape, stype=stype)
        y = sparse_nd_ones(shape, stype)
        z = x > y
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = y > 0
        assert (z.asnumpy() == np.ones(shape)).all()
        z = 0 > y
        assert (z.asnumpy() == np.zeros(shape)).all()


def test_sparse_nd_greater_equal():
    for stype in ['row_sparse', 'csr']:
        shape = rand_shape_2d()
        x = mx.nd.zeros(shape=shape, stype=stype)
        y = sparse_nd_ones(shape, stype)
        z = x >= y
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = y >= 0
        assert (z.asnumpy() == np.ones(shape)).all()
        z = 0 >= y
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = y >= 1
        assert (z.asnumpy() == np.ones(shape)).all()


def test_sparse_nd_lesser():
    for stype in ['row_sparse', 'csr']:
        shape = rand_shape_2d()
        x = mx.nd.zeros(shape=shape, stype=stype)
        y = sparse_nd_ones(shape, stype)
        z = y < x
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = 0 < y
        assert (z.asnumpy() == np.ones(shape)).all()
        z = y < 0
        assert (z.asnumpy() == np.zeros(shape)).all()


def test_sparse_nd_lesser_equal():
    for stype in ['row_sparse', 'csr']:
        shape = rand_shape_2d()
        x = mx.nd.zeros(shape=shape, stype=stype)
        y = sparse_nd_ones(shape, stype)
        z = y <= x
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = 0 <= y
        assert (z.asnumpy() == np.ones(shape)).all()
        z = y <= 0
        assert (z.asnumpy() == np.zeros(shape)).all()
        z = 1 <= y
        assert (z.asnumpy() == np.ones(shape)).all()


def test_sparse_nd_binary():
    N = 10
    def check_binary(fn, stype):
        for _ in range(N):
            ndim = 2
            oshape = np.random.randint(1, 6, size=(ndim,))
            bdim = 2
            lshape = list(oshape)
            rshape = list(oshape[ndim-bdim:])
            for i in range(bdim):
                sep = np.random.uniform(0, 1)
                if sep < 0.33:
                    lshape[ndim-i-1] = 1
                elif sep < 0.66:
                    rshape[bdim-i-1] = 1
            lhs = np.random.uniform(0, 1, size=lshape)
            rhs = np.random.uniform(0, 1, size=rshape)
            lhs_nd = mx.nd.array(lhs).tostype(stype)
            rhs_nd = mx.nd.array(rhs).tostype(stype)
            assert_allclose(fn(lhs, rhs), fn(lhs_nd, rhs_nd).asnumpy(), rtol=1e-4, atol=1e-4)

    stypes = ['row_sparse', 'csr']
    for stype in stypes:
        check_binary(lambda x, y: x + y, stype)
        check_binary(lambda x, y: x - y, stype)
        check_binary(lambda x, y: x * y, stype)
        check_binary(lambda x, y: x / y, stype)
        check_binary(lambda x, y: x ** y, stype)
        check_binary(lambda x, y: x > y, stype)
        check_binary(lambda x, y: x < y, stype)
        check_binary(lambda x, y: x >= y, stype)
        check_binary(lambda x, y: x <= y, stype)
        check_binary(lambda x, y: x == y, stype)


def test_sparse_nd_binary_rop():
    N = 10
    def check(fn, stype):
        for _ in range(N):
            ndim = 2
            shape = np.random.randint(1, 6, size=(ndim,))
            npy = np.random.normal(0, 1, size=shape)
            nd = mx.nd.array(npy).tostype(stype)
            assert_allclose(fn(npy), fn(nd).asnumpy(), rtol=1e-4, atol=1e-4)

    stypes = ['row_sparse', 'csr']
    for stype in stypes:
        check(lambda x: 1 + x, stype)
        check(lambda x: 1 - x, stype)
        check(lambda x: 1 * x, stype)
        check(lambda x: 1 / x, stype)
        check(lambda x: 2 ** x, stype)
        check(lambda x: 1 > x, stype)
        check(lambda x: 0.5 > x, stype)
        check(lambda x: 0.5 < x, stype)
        check(lambda x: 0.5 >= x, stype)
        check(lambda x: 0.5 <= x, stype)
        check(lambda x: 0.5 == x, stype)

def test_sparse_nd_binary_iop():
    N = 10
    def check_binary(fn, stype):
        for _ in range(N):
            ndim = 2
            oshape = np.random.randint(1, 6, size=(ndim,))
            lshape = list(oshape)
            rshape = list(oshape)
            lhs = np.random.uniform(0, 1, size=lshape)
            rhs = np.random.uniform(0, 1, size=rshape)
            lhs_nd = mx.nd.array(lhs).tostype(stype)
            rhs_nd = mx.nd.array(rhs).tostype(stype)
            assert_allclose(fn(lhs, rhs),
                            fn(lhs_nd, rhs_nd).asnumpy(),
                            rtol=1e-4, atol=1e-4)

    def inplace_add(x, y):
        x += y
        return x
    def inplace_mul(x, y):
        x *= y
        return x
    stypes = ['csr', 'row_sparse']
    fns = [inplace_add, inplace_mul]
    for stype in stypes:
        for fn in fns:
            check_binary(fn, stype)

def test_sparse_nd_negate():
    def check_sparse_nd_negate(shape, stype):
        npy = np.random.uniform(-10, 10, rand_shape_2d())
        arr = mx.nd.array(npy).tostype(stype)
        assert_almost_equal(npy, arr.asnumpy())
        assert_almost_equal(-npy, (-arr).asnumpy())

        # a final check to make sure the negation (-) is not implemented
        # as inplace operation, so the contents of arr does not change after
        # we compute (-arr)
        assert_almost_equal(npy, arr.asnumpy())

    shape = rand_shape_2d()
    stypes = ['csr', 'row_sparse']
    for stype in stypes:
        check_sparse_nd_negate(shape, stype)

def test_sparse_nd_broadcast():
    sample_num = 1000
    # TODO(haibin) test with more than 2 dimensions
    def test_broadcast_to(stype):
        for i in range(sample_num):
            ndim = 2
            target_shape = np.random.randint(1, 11, size=ndim)
            shape = target_shape.copy()
            axis_flags = np.random.randint(0, 2, size=ndim)
            axes = []
            for (axis, flag) in enumerate(axis_flags):
                if flag:
                    shape[axis] = 1
            dat = np.random.rand(*shape) - 0.5
            numpy_ret = dat
            ndarray = mx.nd.array(dat).tostype(stype)
            ndarray_ret = ndarray.broadcast_to(shape=target_shape)
            if type(ndarray_ret) is mx.ndarray.NDArray:
                ndarray_ret = ndarray_ret.asnumpy()
            assert (ndarray_ret.shape == target_shape).all()
            err = np.square(ndarray_ret - numpy_ret).mean()
            assert err < 1E-8
    stypes = ['csr', 'row_sparse']
    for stype in stypes:
        test_broadcast_to(stype)


def test_sparse_nd_transpose():
    npy = np.random.uniform(-10, 10, rand_shape_2d())
    stypes = ['csr', 'row_sparse']
    for stype in stypes:
        nd = mx.nd.array(npy).tostype(stype)
        assert_almost_equal(npy.T, (nd.T).asnumpy())

def test_sparse_nd_output_fallback():
    shape = (10, 10)
    out = mx.nd.zeros(shape=shape, stype='row_sparse')
    mx.nd.random.normal(shape=shape, out=out)
    assert(np.sum(out.asnumpy()) != 0)

def test_sparse_nd_random():
    """ test sparse random operator on cpu """
    # gpu random operator doesn't use fixed seed
    if default_context().device_type is 'gpu':
        return
    shape = (100, 100)
    fns = [mx.nd.random.uniform, mx.nd.random.normal, mx.nd.random.gamma]
    for fn in fns:
        rsp_out = mx.nd.zeros(shape=shape, stype='row_sparse')
        dns_out = mx.nd.zeros(shape=shape, stype='default')
        mx.random.seed(0)
        np.random.seed(0)
        fn(shape=shape, out=dns_out)
        mx.random.seed(0)
        np.random.seed(0)
        fn(shape=shape, out=rsp_out)
        assert_almost_equal(dns_out.asnumpy(), rsp_out.asnumpy())


def test_sparse_nd_astype():
    stypes = ['row_sparse', 'csr']
    for stype in stypes:
        x = mx.nd.zeros(shape=rand_shape_2d(), stype=stype, dtype='float32')
        y = x.astype('int32')
        assert(y.dtype == np.int32), y.dtype


def test_sparse_nd_pickle():
    np.random.seed(0)
    repeat = 10
    dim0 = 40
    dim1 = 40
    stypes = ['row_sparse', 'csr']
    densities = [0, 0.01, 0.1, 0.2, 0.5]
    stype_dict = {'row_sparse': RowSparseNDArray, 'csr': CSRNDArray}
    for _ in range(repeat):
        shape = rand_shape_2d(dim0, dim1)
        for stype in stypes:
            for density in densities:
                a, _ = rand_sparse_ndarray(shape, stype, density)
                assert isinstance(a, stype_dict[stype])
                data = pkl.dumps(a)
                b = pkl.loads(data)
                assert isinstance(b, stype_dict[stype])
                assert same(a.asnumpy(), b.asnumpy())


def test_sparse_nd_save_load():
    np.random.seed(0)
    repeat = 1
    stypes = ['default', 'row_sparse', 'csr']
    stype_dict = {'default': NDArray, 'row_sparse': RowSparseNDArray, 'csr': CSRNDArray}
    num_data = 20
    densities = [0, 0.01, 0.1, 0.2, 0.5]
    fname = 'tmp_list.bin'
    for _ in range(repeat):
        data_list1 = []
        for i in range(num_data):
            stype = stypes[np.random.randint(0, len(stypes))]
            shape = rand_shape_2d(dim0=40, dim1=40)
            density = densities[np.random.randint(0, len(densities))]
            data_list1.append(rand_ndarray(shape, stype, density))
            assert isinstance(data_list1[-1], stype_dict[stype])
        mx.nd.save(fname, data_list1)

        data_list2 = mx.nd.load(fname)
        assert len(data_list1) == len(data_list2)
        for x, y in zip(data_list1, data_list2):
            assert same(x.asnumpy(), y.asnumpy())

        data_map1 = {'ndarray xx %s' % i: x for i, x in enumerate(data_list1)}
        mx.nd.save(fname, data_map1)
        data_map2 = mx.nd.load(fname)
        assert len(data_map1) == len(data_map2)
        for k, x in data_map1.items():
            y = data_map2[k]
            assert same(x.asnumpy(), y.asnumpy())
    os.remove(fname)

def test_sparse_nd_unsupported():
    nd = mx.nd.zeros((2,2), stype='row_sparse')
    fn_slice = lambda x: x._slice(None, None)
    fn_at = lambda x: x._at(None)
    fn_reshape = lambda x: x.reshape(None)
    fns = [fn_slice, fn_at, fn_reshape]
    for fn in fns:
        try:
            fn(nd)
            assert(False)
        except:
            pass

def test_create_csr():
    dim0 = 50
    dim1 = 50
    densities = [0, 0.01, 0.1, 0.2, 0.5]
    for density in densities:
        shape = rand_shape_2d(dim0, dim1)
        matrix = rand_ndarray(shape, 'csr', density)
        data = matrix.data
        indptr = matrix.indptr
        indices = matrix.indices
        csr_created = mx.nd.sparse.csr_matrix(data=data, indptr=indptr,
                                              indices=indices, shape=shape)
        assert csr_created.stype == 'csr'
        assert same(csr_created.data.asnumpy(), data.asnumpy())
        assert same(csr_created.indptr.asnumpy(), indptr.asnumpy())
        assert same(csr_created.indices.asnumpy(), indices.asnumpy())
        csr_copy = mx.nd.array(csr_created)
        assert(same(csr_copy.asnumpy(), csr_created.asnumpy()))


def test_create_row_sparse():
    dim0 = 50
    dim1 = 50
    densities = [0, 0.01, 0.1, 0.2, 0.5]
    for density in densities:
        shape = rand_shape_2d(dim0, dim1)
        matrix = rand_ndarray(shape, 'row_sparse', density)
        data = matrix.data
        indices = matrix.indices
        rsp_created = mx.nd.sparse.row_sparse_array(data=data, indices=indices, shape=shape)
        assert rsp_created.stype == 'row_sparse'
        assert same(rsp_created.data.asnumpy(), data.asnumpy())
        assert same(rsp_created.indices.asnumpy(), indices.asnumpy())
        rsp_copy = mx.nd.array(rsp_created)
        assert(same(rsp_copy.asnumpy(), rsp_created.asnumpy()))

def test_sparse_nd_empty():
    stypes = ['csr', 'row_sparse', 'default']
    for stype in stypes:
        nd = mx.nd.empty((2,2), stype=stype)
        assert(nd.stype == stype)


def test_synthetic_dataset_generator():
    def test_powerlaw_generator(csr_arr, final_row=1):
        """Test power law distribution
        Total Elements: 32000, Number of zeros: 3200
        Every row has 2 * non zero elements of the previous row.
        Also since (2047 < 3200 < 4095) this will be true till 10th row"""
        indices = csr_arr.indices.asnumpy()
        indptr = csr_arr.indptr.asnumpy()
        for row in range(1, final_row + 1):
            nextrow = row + 1
            current_row_nnz = indices[indptr[row] - 1] + 1
            next_row_nnz = indices[indptr[nextrow] - 1] + 1
            assert next_row_nnz == 2 * current_row_nnz

    # Test if density is preserved
    csr_arr_cols, _ = rand_sparse_ndarray(shape=(32, 10000), stype="csr",
                                          density=0.01, distribution="powerlaw")

    csr_arr_small, _ = rand_sparse_ndarray(shape=(5, 5), stype="csr",
                                           density=0.5, distribution="powerlaw")

    csr_arr_big, _ = rand_sparse_ndarray(shape=(32, 1000000), stype="csr",
                                         density=0.4, distribution="powerlaw")

    csr_arr_square, _ = rand_sparse_ndarray(shape=(1600, 1600), stype="csr",
                                            density=0.5, distribution="powerlaw")
    assert len(csr_arr_cols.data) == 3200
    test_powerlaw_generator(csr_arr_cols, final_row=9)
    test_powerlaw_generator(csr_arr_small, final_row=1)
    test_powerlaw_generator(csr_arr_big, final_row=4)
    test_powerlaw_generator(csr_arr_square, final_row=6)


if __name__ == '__main__':
    import nose
    nose.runmodule()
