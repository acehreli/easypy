import pytest
from time import sleep
from easypy.threadtree import get_thread_stacks, ThreadContexts, UUIDS_TREE, IDENT_TO_UUID, UUID_TO_IDENT
from easypy.concurrency import concurrent, MultiObject, MultiException


@pytest.fixture(autouse=True, scope="module")
def ensure_no_leak():
    collections = (UUIDS_TREE, IDENT_TO_UUID, UUID_TO_IDENT)

    from threading import get_ident
    ident = get_ident()

    # with concurrent(lambda: None):
    #     pass
    before = [set(c) for c in collections]

    yield
    sleep(1)

    after = [set(c) for c in collections]

    non_leak = {ident, IDENT_TO_UUID.get(ident)}
    assert [c-non_leak for c in before] == [c-non_leak for c in after]


def test_thread_stacks():
    with concurrent(sleep, .1, threadname='sleep'):
        print(get_thread_stacks().render())


def test_thread_contexts_counters():
    TC = ThreadContexts(counters=('i', 'j'))
    assert TC.i == TC.j == 0

    with TC(i=1):
        def check1():
            assert TC.i == 1
            assert TC.j == 0

            with TC(i=1, j=1):
                def check2():
                    assert TC.i == 2
                    assert TC.j == 1
                with concurrent(check2):
                    pass

        with concurrent(check1):
            pass


def test_thread_context_stacks():
    TC = ThreadContexts(stacks=('i', 'j'))
    assert TC.i == TC.j == []

    with TC(i='a'):
        def check1():
            assert TC.i == ['a']
            assert TC.j == []

            with TC(i='i', j='j'):
                def check2():
                    assert TC.i == ['a', 'i']
                    assert TC.j == ['j']
                with concurrent(check2):
                    pass

        with concurrent(check1):
            pass


def test_multiobject_1():
    m = MultiObject(range(10))

    def mul(a, b, *c):
        return a*b + sum(c)

    assert sum(m.call(mul, 2)) == 90
    assert sum(m.call(mul, b=10)) == 450
    assert sum(m.call(mul, 1, 1, 1)) == 65

    assert m.filter(None).L == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert sum(m.denominator) == 10

    with pytest.raises(MultiException) as info:
        m.call(lambda i: 1 / (i % 2))

    assert info.value.count == 5
    assert info.value.common_type == ZeroDivisionError
    assert not info.value.complete


def test_multiobject_concurrent_find_found():
    m = MultiObject(range(10))
    from time import sleep
    ret = m.concurrent_find(lambda n: sleep(n/10) or n)  # n==0 is not nonzero, so it's not eligible
    assert ret == 1


def test_multiobject_concurrent_find_not_found():
    m = MultiObject(range(10))
    ret = m.concurrent_find(lambda n: n < 0)
    assert ret is False

    m = MultiObject([0]*5)
    ret = m.concurrent_find(lambda n: n)
    assert ret is 0
