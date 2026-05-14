from operator import add, mul

def addmore(*rest):
    sum = 0
    for x in rest:
        sum = add(sum, x)
    return sum

def mulmore(*rest):
    product = 1
    for x in rest:
        product = mul(product, x)
    return product

def curry2(f):
    def g(x):
        def h(y):
            return f(x, y)
        return h
    return g

def curryn(f, n):
    try:
        n = int(str(n))
    except ValueError:
        raise ValueError("n must be an integer")
    if n < 2 or not callable(f):
        raise ValueError("n must be at least 2 and f must be a callable")
    if n == 2:
        return curry2(f)

    def g(x):
        return curryn(lambda *rest: f(x, *rest), n - 1)

    return g

print(curry2(add)(3)(4))
print(curry2(mul)(3)(4))
# add and mul only take two arguments; curryn(f, 3) needs f to accept three.
print(curryn(addmore, 3)(3)(4)(5))
print(curryn(mulmore, 3)(3)(4)(5))
