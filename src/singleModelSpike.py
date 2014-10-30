from numpy import logical_not, sqrt, ones, logspace, linspace, inf, newaxis, log2, median, argmin, eye, diag, dot
from numpy.linalg import norm, svd
from math import floor, log10, ceil
from numpy.numarray import arange
import numpy as np
from numpy.random import randn
from numpy import array, zeros, allclose
from minL2PenalizedLossOverSimplex import weightsForLosses, penalizedMultipleWeightedLoss2
from robust_pca import shrinkage_pca
from weightedModelTypes import MultiLinearRegressionState, ClusteringState, MultiPCAState
from utility import squaredColNorm, nonNegativePart
from random import sample
import matplotlib.pyplot as plt


def create_regression_task(d, n, noise_strength, alt_source_strength, noisy_proportion=0.1):
    X = randn(d, n) / np.sqrt(d)
    rgt = np.zeros(d)
    rgt[0] = 1
    rns = randn(d) / np.sqrt(d)
    #print("rns = %s" % rns)
    y = rgt.dot(X) + randn(n) / 10
    first_outlier = int(ceil((1 - noisy_proportion) * n))
    #print("first_outlier = %s" % first_outlier)
    outlier_mods = rns.dot(X[:, first_outlier:]) * alt_source_strength + \
        randn(n - first_outlier) * noise_strength
    #print("outlier_mods %s" % outlier_mods)
    y[first_outlier:] += outlier_mods
    return X, y, rgt


def experiment_matrix_results(make_data, row_param_values, col_param_values, methods, summarize):
    n_cols = col_param_values.shape[0]
    n_rows = row_param_values.shape[0]
    result_matrices = [ones((n_rows, n_cols)) * inf for _ in methods]
    for ip, noise_prop in enumerate(col_param_values):
        for io, offset in enumerate(row_param_values):
            print("."),
            data, gt = make_data(offset, noise_prop)
            for i, (m, _) in enumerate(methods):
                estimate = m(data)
                result_matrices[i][io, ip] = summarize(estimate, gt)
        print(".")
    method_names = [n for (m, n) in methods]
    return result_matrices, method_names


def annoying_pca_data(dimension, big_dims, total_samples, noisy_proportion, noise_level, disturbance_level):
    # Base data
    noise_scale = dimension ** -0.5
    scales = ones(dimension) * noise_scale * noise_level
    scales[:big_dims] = big_dims ** -0.5
    X = randn(total_samples, dimension).dot(diag(scales))

    # Adding disturbance
    noisy_samples = int(floor(total_samples * noisy_proportion))
    A = zeros((dimension, dimension))
    A[-1, 0] = 1
    X[:noisy_samples, :] += A.dot(X[:noisy_samples, :].T).T * disturbance_level

    return X, eye(dimension)


def angleCosinesBetweenBases(baseForFirst, baseForSecond):
    prod = dot(baseForFirst.transpose(), baseForSecond)
    _, s, _ = svd(prod, full_matrices=False)
    return s


def pca_experiment_matrix_results(big_dim, d, samples, noisy_proportions, disturbance_levels):
    def make_task(noise_prop, dist_lvl):
        X, gt_basis = annoying_pca_data(d, big_dim, samples, noise_prop, 0.1, dist_lvl)
        return X, gt_basis

    def score(basis, gt_basis):
        return norm(1 - angleCosinesBetweenBases(basis[:, :big_dim], gt_basis[:, :big_dim]))

    def l1regularized_correction0(X):
        return shrinkage_pca(X, big_dim, 1).U

    def l1regularized_correction2(X):
        return shrinkage_pca(X, big_dim, 0.01).U

    def weighted(X):
        beta = 1
        return weighted_pca(X.T, big_dim).U

    def standard(X):
        samples, _ = X.shape
        u = ones(samples) / samples
        return (MultiPCAState(X.T, u, modelParameters={'d': big_dim})).U

    return experiment_matrix_results(make_task, noisy_proportions, disturbance_levels,
                                     [(weighted, "RW"),
                                      (l1regularized_correction2, r"l1 reg. $\lambda = $ 0.01."),
                                      (l1regularized_correction0, r"l1 reg. $\lambda = $ 1."),
                                      (standard, "PCA")],
                                     score)


def display_result_matrices(matrices, method_names, row_vals, col_vals, ylabel, xlabel):
    matrices = [np.log10(m) for m in matrices]
    high = max([m.max() for m in matrices])
    low = min([m.min() for m in matrices])
    n_methods = len(method_names)

    fig, axes = plt.subplots(nrows=1, ncols=n_methods)

    for i, (m, n, ax) in enumerate(zip(matrices, method_names, axes.flat)):
        plt.subplot(1, n_methods, i+1)
        im = plt.imshow(m, cmap=plt.cm.gray_r, vmin=low, vmax=high, interpolation='nearest')
        plt.title(n)
        plt.xticks(arange(col_vals.shape[0]), ["%.2f" % cv for cv in col_vals], rotation=70)
        plt.xlabel(xlabel)  # Can share via:
        # http://stackoverflow.com/questions/6963035/pyplot-axes-labels-for-subplots
        if i == 0:
            plt.yticks(arange(row_vals.shape[0]), ["%.2f" % rv for rv in row_vals])
            plt.ylabel(ylabel)
        else:
            plt.yticks([])
    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.82, 0.4, 0.03, 0.2])
    fig.colorbar(im, cax=cbar_ax)


def linear_regression_experiment_matrix_results(d, n, noise_strengths, alt_src_strengths):
    def make_task(noise_str, alt_src_str):
        X, y, rgt = create_regression_task(d, n, noise_str, alt_src_str)
        return (X, y), rgt

    def score(r, rgt):
        return norm(r - rgt)

    def l1regularized_correction(data):
        X, y = data
        return l1regularized_correction_regression(X.T, y, 0.1)

    def weighted(data):
        X, y = data
        return weighted_regression2(X.T, y).r

    return experiment_matrix_results(make_task, noise_strengths, alt_src_strengths, [weighted, l1regularized_correction], score)


def linear_regression_experiment_matrix_results2(d, n, noisy_props, alt_src_strengths):
    def make_task(noisy_prop, alt_src_str):
        X, y, rgt = create_regression_task(d, n, 0.1, alt_src_str, noisy_proportion=noisy_prop)
        return (X, y), rgt

    def score(r, rgt):
        return norm(r - rgt)

    def l1regularized_correction(data):
        X, y = data
        return l1regularized_correction_regression(X.T, y, 0.1)

    def weighted(data):
        X, y = data
        return weighted_regression2(X.T, y).r

    def regular(data):
        X, y = data
        n, d = X.T.shape
        u = ones(n) / n
        s = MultiLinearRegressionState((X, y), u, {'regularizationStrength': 0})
        return s.r

    return experiment_matrix_results(make_task, noisy_props, alt_src_strengths,
                                     [(weighted, "RW loss."),
                                     (l1regularized_correction, "l1 reg. data adj."),
                                     (regular, "std. regression.")],
                                     score)


def l1regularized_correction_regression(point_rows, y, eps):
    n, d = point_rows.shape
    u = ones(n) / n
    s = MultiLinearRegressionState((point_rows.T, y), u, {'regularizationStrength': 0})
    r = s.r
    old_r = zeros(d)
    while not allclose(old_r, r):
        old_r = r
        predicted_y = r.dot(point_rows.T)
        correction = soft_shrink_rows((predicted_y - y)[:, np.newaxis], eps).flatten()
        f_y = correction + y
        s = MultiLinearRegressionState((point_rows.T, f_y), u, modelParameters={'regularizationStrength': 0})
        r = s.r
    return r


def weighted_regression2(point_rows, y):
    s, beta = weighted_model((point_rows.T, y), MultiLinearRegressionState, {'regularizationStrength': 0})
    #print("beta is %s" % beta)
    n = s.weights.shape[0]
    #print("norm(w-1/n) * sqrt(n) = %s" % (norm(s.weights - (ones(n) / n)) * sqrt(n)))
    return s


def location_estimation(data, beta):
    s = weighted_modeling(data, ClusteringState, None, beta)
    return s.center


def location_estimation2(data):
    s, beta = weighted_model(data, ClusteringState, None)
    #print("beta is %s" % beta)
    #n = s.weights.shape[0]
    #print("norm(w-1/n) * sqrt(n) = %s" % (norm(s.weights - (ones(n) / n)) * sqrt(n)))
    return s.center


def weighted_pca(data, d):
    s, beta = weighted_model(data, MultiPCAState, {'d': d})
    return s


def weighted_model(data, model_class, model_parameters, algorithm='unif_then_average_loss'):

    algs = {'unif_then_average_loss': weighted_model_find_beta2,
            'beta_68th': weighted_model_find_beta3,
            'w_distance': weighted_model_find_beta}

    if algorithm in algs:
        return algs[algorithm](data, model_class, model_parameters)
    else:
        error("no such algorithm")


def weighted_model_find_beta(data, model_class, model_parameters):
    beta = 1.
    s = weighted_modeling(data, model_class, model_parameters, beta)
    n = s.weights.shape[0]

    def w_distance(s):
        return sqrt((norm((n * s.weights) - 1) ** 2) / n)

    max_distance = 1.1
    #plt.plot(s.weights, label='wdis = {0:f}, beta = {1:f}, werr = {2:f}'.format(w_distance(s), beta,
    #                                                                            s.weights.dot(s.squaredLosses())))
    if w_distance(s) > max_distance:
        print("started at w_dis = %s, doubling beta" % w_distance(s))
        while w_distance(s) > max_distance:
            beta *= 2
            s = weighted_modeling(data, model_class, model_parameters, beta)
            #print("w_dis = %s, at beta = %f" % (w_distance(s), beta))
        print("finished at w_dis = %s" % w_distance(s))
    else:
        print("started at w_dis = %s, halving beta" % w_distance(s))
        while w_distance(s) <= max_distance:
            beta /= 2
            s = weighted_modeling(data, model_class, model_parameters, beta)
            print("w_dis = %s, at beta = %f, werr: %f" % (w_distance(s), beta, s.weights.dot(s.squaredLosses())))
            #plt.plot(s.weights, label='wdis = {0:f}, beta = {1:f}, werr = {2:f}'.format(w_distance(s), beta,
            #                                                                            s.weights.dot(s.squaredLosses())))

        print("finished at w_dis = %s, doubling once." % w_distance(s))
        beta *= 2
        s = weighted_modeling(data, model_class, model_parameters, beta)
        print("final w_dis = %s, doubling once." % w_distance(s))
        #plt.legend(loc='best')
    #plt.show()
    return s, beta


def weighted_model_find_beta2(data, model_class, model_parameters):
    beta = 1e6
    s = weighted_modeling(data, model_class, model_parameters, beta)
    n = s.weights.shape[0]
    u = ones(n) / n
    uni_s = model_class(data, u, model_parameters)

    beta = uni_s.weights.dot(uni_s.squaredLosses())
    s = weighted_modeling(data, model_class, model_parameters, beta)
    return s, beta


def weighted_model_find_beta3(data, model_class, model_parameters):
    beta = 1e6
    s = weighted_modeling(data, model_class, model_parameters, beta)
    n = s.weights.shape[0]
    u = ones(n) / n
    s = model_class(data, u, model_parameters)
    typ_loss = np.percentile(s.squaredLosses(), 68)
    # Try to use lower beta
    while typ_loss < beta:
        old_beta = beta
        beta = typ_loss
        s = weighted_modeling(data, model_class, model_parameters, beta)
        typ_loss = np.percentile(s.squaredLosses(), 68)

    # Last change didn't improve things, go back once
    s = weighted_modeling(data, model_class, model_parameters, old_beta)
    return s, old_beta


def weighted_modeling(data, model_class, model_parameters, beta, n_init=10):
    best_joint_loss = inf
    best_state = None
    for t in range(n_init):
        L = model_class.randomModelLosses(data, 1, model_parameters)
        n = L.shape[0]
        _, samples = L.shape
        alpha = beta * samples
        w = weightsForLosses(L[0, :], alpha)
        w_old = zeros(samples)
        s = None
        while not allclose(w, w_old):
            w_old = w
            s = model_class(data, w, modelParameters=model_parameters)
            w = weightsForLosses(s.squaredLosses(), alpha)
        L = s.squaredLosses()
        joint_loss = penalizedMultipleWeightedLoss2(L[newaxis, :], w[newaxis, :], beta * n)
        if best_joint_loss > joint_loss:
            best_joint_loss = joint_loss
            best_state = s
    return best_state


def l1regularized_correction_clustering(X, k, eps):
    n, dim = X.shape
    centers = (X.T[:, sample(range(n), k)]).T
    L = array([squaredColNorm((X - center).T) for center in centers])
    meps = sqrt(L.max()) / 3
    #print("meps is %s" % meps)
    steps = max(3, int(log2(meps / eps)))
    #print("steps is %s" % steps)
    epses = logspace(log10(eps), log10(meps), steps)[::-1]
    #print("epses are %s" % epses)
    r = 0
    best_centers = None
    for ceps in epses:
        old_centers = zeros((k, dim))
        #print("Using ceps = %s" % ceps),
        while not allclose(centers, old_centers):
            r += 1
            #print("."),
            if r > 100:
                #print "max abs diff in centers: %s" % np.abs(old_centers - centers).max()
                r = 0
            old_centers = centers
            L = array([squaredColNorm((X - center).T) for center in centers])
            best_centers = L.argmin(axis=0)
            diffs = centers[best_centers, :] - X
            fixed = soft_shrink_rows(diffs, ceps) + X
            centers = array([fixed[best_centers == j, :].mean(axis=0) for j in range(k)])
        #print(":")
    #print("Done")
    return centers, best_centers


def location_data_one_sided_noise(d, noise_offset, noisy_proportion=0.1):
    num_points = 1000
    data_per_column = randn(d, num_points) / sqrt(d)
    first_outlier = int(floor((1 - noisy_proportion) * num_points))
    data_per_column[0, first_outlier:num_points] *= 10
    data_per_column[0, first_outlier:num_points] += noise_offset
    return data_per_column


def soft_shrink_rows(X, length):
    """ Reduce the Euclidean norm of rows of X by length (down to zero). """
    curr_row_lengths = np.sqrt(squaredColNorm(X.T))
    # trivial rows are unmodified:
    tr = logical_not(curr_row_lengths > 0)
    divisors = curr_row_lengths
    divisors[tr] = 1
    unit_length_rows = (X.T / divisors).T
    desired_lengths = nonNegativePart(curr_row_lengths - length)
    return (unit_length_rows.T * desired_lengths).T


def location_estimation_experiment_results(d, noise_proportions, noise_offsets):
    def make_task(noise_prop, noise_offset):
        data_point_per_column = location_data_one_sided_noise(d, noise_offset=noise_offset, noisy_proportion=noise_prop)
        gt = zeros(d)
        return data_point_per_column, gt

    def score(x, xgt):
        return norm(x-xgt)

    def l1regularized_correction(data_point_per_column):
        hb_centers, hb_labels = l1regularized_correction_clustering(data_point_per_column.T, 1, 0.01)
        return hb_centers[0]

    def weighted(data_point_per_column):
        rw2_center = location_estimation2(data_point_per_column)
        return rw2_center

    def regular(data_point_per_column):
        return data_point_per_column.mean(axis=1)

    return experiment_matrix_results(make_task, noise_proportions, noise_offsets,
                                     [(l1regularized_correction, "l1 reg. data adj."),
                                     (weighted, "RW loss."),
                                     (regular, "std. averaging.")],
                                     score)