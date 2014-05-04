from numpy.random import rand, randn, randint
from numpy import cumsum, ceil, array, repeat, zeros, tile, linspace

d = 10
k = 10
n = 1000



def make_clustered_points(d,k,n):
    """
    >>> X, labels, centers = make_clustered_points(1,2,3)
    >>> X.shape
    (1, 3)
    >>> labels.shape
    (3,)
    >>> centers.shape
    (1, 2)
    >>> labels[-1]
    2
    """
    X = randn(d,n)
    magnitude = array(randint(100,size=n))
    small = array([m in range(0,90) for m in magnitude])
    medium = array([m in range(91,99) for m in magnitude])
    large = array([m in range(99,100) for m in magnitude])

    X[:,small] *= 0.1
    X[:,medium] *= 2.
    X[:,large] *= 10.

    #idxes = cumsum(rand(k))
    #idxes /= (idxes[-1] / n)
    #idxes = ceil(idxes).astype(int)
    idxes = linspace(0,n,k+1)[1:]
    centers = randn(d, k)
    labels = zeros(n)

    for j,(start,end) in enumerate([(0,idxes[0])]+zip(idxes[:-1],idxes[1:])):
        center = tile(centers[:,j], [end - start,1]).T
        X[:, start:end] += center
        labels[start:end] = j

    return X, labels, centers

if __name__ == "__main__":
    import simpleInterface as si
    X,_,_ = make_clustered_points(d,k,n)
    centers, labels = si.clustering(X.T,k, 100*n, n_init=1)
